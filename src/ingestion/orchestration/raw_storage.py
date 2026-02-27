"""
Raw storage layer — writes immutable JSON snapshots to Azure Data Lake Gen2.
Partitioned by: tenant_id / connector / year / month / day / subscription_id.json
Falls back to local filesystem when AZURE_STORAGE_ACCOUNT_NAME is not configured.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_LOCAL_RAW_DIR = Path("data/raw")


def _local_path(
    tenant_id: str,
    connector: str,
    subscription_id: str,
    snapshot_time: datetime,
) -> Path:
    dt = snapshot_time.strftime("%Y/%m/%d")
    return _LOCAL_RAW_DIR / tenant_id / connector / dt / f"{subscription_id}.json"


class RawStorageWriter:
    """
    Writes raw API responses to storage.
    Uses Azure Data Lake Gen2 when configured, local filesystem otherwise.
    """

    def __init__(self) -> None:
        self._use_azure = bool(os.getenv("AZURE_STORAGE_ACCOUNT_NAME"))
        if self._use_azure:
            from azure.identity import DefaultAzureCredential
            from azure.storage.filedatalake import DataLakeServiceClient

            account = os.environ["AZURE_STORAGE_ACCOUNT_NAME"]
            container = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "raw")
            credential = DefaultAzureCredential()
            self._service_client = DataLakeServiceClient(
                account_url=f"https://{account}.dfs.core.windows.net",
                credential=credential,
            )
            self._container = container

    async def write(
        self,
        tenant_id: str,
        connector: str,
        subscription_id: str,
        data: list[dict[str, Any]],
        snapshot_time: datetime | None = None,
    ) -> str:
        """
        Write data as JSON to the raw layer.
        Returns the path/URL where data was written.
        """
        ts = snapshot_time or datetime.now(tz=timezone.utc)
        payload = {
            "snapshot_time": ts.isoformat(),
            "tenant_id": tenant_id,
            "subscription_id": subscription_id,
            "connector": connector,
            "record_count": len(data),
            "data": data,
        }

        if self._use_azure:
            return await self._write_azure(tenant_id, connector, subscription_id, ts, payload)
        return self._write_local(tenant_id, connector, subscription_id, ts, payload)

    def _write_local(
        self,
        tenant_id: str,
        connector: str,
        subscription_id: str,
        ts: datetime,
        payload: dict[str, Any],
    ) -> str:
        path = _local_path(tenant_id, connector, subscription_id, ts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        logger.debug("raw_storage_written_local", path=str(path), records=payload["record_count"])
        return str(path)

    async def _write_azure(
        self,
        tenant_id: str,
        connector: str,
        subscription_id: str,
        ts: datetime,
        payload: dict[str, Any],
    ) -> str:
        dt = ts.strftime("%Y/%m/%d")
        file_path = f"{tenant_id}/{connector}/{dt}/{subscription_id}.json"
        content = json.dumps(payload, indent=2, default=str).encode("utf-8")

        fs_client = self._service_client.get_file_system_client(self._container)
        file_client = fs_client.get_file_client(file_path)
        file_client.upload_data(content, overwrite=True)

        uri = f"abfss://{self._container}@{os.environ['AZURE_STORAGE_ACCOUNT_NAME']}.dfs.core.windows.net/{file_path}"
        logger.debug("raw_storage_written_azure", uri=uri, records=payload["record_count"])
        return uri
