"""
Base connector with retry, exponential backoff, 429 throttle handling,
pagination support, structured logging, and DefaultAzureCredential management.
"""
from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog
from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
import logging

logger = structlog.get_logger(__name__)

# Retry on transient HTTP errors and throttling
RETRIABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 5
BACKOFF_MIN_SECONDS = 1
BACKOFF_MAX_SECONDS = 60
AZURE_MGMT_SCOPE = "https://management.azure.com/.default"


class ThrottleError(Exception):
    """Raised when Azure API returns 429 Too Many Requests."""
    def __init__(self, retry_after: int = 30):
        self.retry_after = retry_after
        super().__init__(f"Rate limited — retry after {retry_after}s")


class ConnectorError(Exception):
    """Raised for unrecoverable connector errors."""


@dataclass
class ConnectorContext:
    """Execution context passed to every connector call."""
    tenant_id: str
    subscription_id: str
    correlation_id: str = ""
    operation_name: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class AzureHttpClient:
    """
    Async HTTP client for Azure REST APIs.
    - Manages access token lifecycle
    - Handles 429 with Retry-After header
    - Retries on transient errors with exponential backoff
    - Logs all requests with duration_ms
    """

    def __init__(self, credential: TokenCredential, scope: str = AZURE_MGMT_SCOPE):
        self._credential = credential
        self._scope = scope
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._client = httpx.AsyncClient(timeout=60.0)

    async def _get_token(self) -> str:
        """Return a valid access token, refreshing if within 60s of expiry."""
        now = time.monotonic()
        if self._token and now < self._token_expires_at - 60:
            return self._token

        token_obj = self._credential.get_token(self._scope)
        self._token = token_obj.token
        self._token_expires_at = token_obj.expires_on
        return self._token

    async def request(
        self,
        method: str,
        url: str,
        ctx: ConnectorContext,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make an authenticated Azure API request with retry + throttle handling.
        Returns parsed JSON response body.
        """
        token = await self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if ctx.correlation_id:
            headers["x-ms-correlation-request-id"] = ctx.correlation_id

        start = time.perf_counter()
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await self._client.request(
                    method, url, headers=headers, json=json, params=params
                )
                duration_ms = round((time.perf_counter() - start) * 1000, 2)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 30))
                    logger.warning(
                        "azure_api_throttled",
                        url=url,
                        attempt=attempt,
                        retry_after_s=retry_after,
                        tenant_id=ctx.tenant_id,
                        subscription_id=ctx.subscription_id,
                        operation_name=ctx.operation_name,
                    )
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(retry_after)
                        token = await self._get_token()
                        headers["Authorization"] = f"Bearer {token}"
                        continue
                    raise ThrottleError(retry_after)

                if response.status_code in RETRIABLE_STATUS_CODES - {429}:
                    backoff = min(BACKOFF_MIN_SECONDS * (2 ** (attempt - 1)), BACKOFF_MAX_SECONDS)
                    logger.warning(
                        "azure_api_transient_error",
                        status_code=response.status_code,
                        url=url,
                        attempt=attempt,
                        backoff_s=backoff,
                        tenant_id=ctx.tenant_id,
                    )
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(backoff)
                        continue
                    response.raise_for_status()

                response.raise_for_status()

                logger.info(
                    "azure_api_request",
                    method=method,
                    url=url,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    attempt=attempt,
                    tenant_id=ctx.tenant_id,
                    subscription_id=ctx.subscription_id,
                    operation_name=ctx.operation_name,
                )
                return response.json()

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                backoff = min(BACKOFF_MIN_SECONDS * (2 ** (attempt - 1)), BACKOFF_MAX_SECONDS)
                logger.warning(
                    "azure_api_network_error",
                    error=str(exc),
                    attempt=attempt,
                    backoff_s=backoff,
                    url=url,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(backoff)
                    continue
                raise ConnectorError(f"Network error after {MAX_RETRIES} attempts: {exc}") from exc

        raise ConnectorError(f"Exhausted {MAX_RETRIES} retries for {url}")

    async def paginate(
        self,
        method: str,
        url: str,
        ctx: ConnectorContext,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        value_key: str = "value",
        next_link_key: str = "nextLink",
    ) -> list[dict[str, Any]]:
        """
        Auto-paginate an Azure API endpoint that uses nextLink continuation.
        Supports 100+ subscriptions / large result sets.
        """
        results: list[dict[str, Any]] = []
        current_url: str | None = url
        current_json = json
        current_params = params
        page = 0

        while current_url:
            page += 1
            data = await self.request(
                method, current_url, ctx, json=current_json, params=current_params
            )
            page_items = data.get(value_key, [])
            results.extend(page_items)

            logger.debug(
                "azure_api_page",
                page=page,
                items_on_page=len(page_items),
                total_so_far=len(results),
                operation_name=ctx.operation_name,
                tenant_id=ctx.tenant_id,
            )

            current_url = data.get(next_link_key)
            # nextLink already contains all query params — clear them for subsequent pages
            current_json = None
            current_params = None

        return results

    async def close(self) -> None:
        await self._client.aclose()


class BaseConnector(ABC):
    """
    Abstract base for all AzCops Azure data connectors.
    Subclasses implement `collect()` which returns raw data plus mapped records.
    """

    def __init__(self, credential: TokenCredential | None = None):
        self._credential = credential or DefaultAzureCredential()
        self._http = AzureHttpClient(self._credential)

    @abstractmethod
    async def collect(self, ctx: ConnectorContext) -> list[dict[str, Any]]:
        """
        Collect data for a single subscription.
        Returns a list of normalised record dicts ready for DB upsert.
        """
        ...

    async def close(self) -> None:
        await self._http.close()

    async def __aenter__(self) -> "BaseConnector":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()
