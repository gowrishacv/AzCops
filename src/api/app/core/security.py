from dataclasses import dataclass

import httpx
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

security_scheme = HTTPBearer(auto_error=False)

_jwks_cache: dict | None = None


@dataclass
class CurrentUser:
    """Represents the authenticated user from JWT claims."""

    sub: str
    name: str
    email: str
    tenant_id: str
    roles: list[str]


async def _get_jwks() -> dict:
    """Fetch and cache JWKS from Entra ID."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    jwks_url = f"https://login.microsoftonline.com/{settings.azure_tenant_id}/discovery/v2.0/keys"
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url, timeout=10)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache


def _decode_token(token: str, jwks: dict) -> dict:
    """Decode and validate a JWT token against JWKS."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    rsa_key = {}
    for key in jwks.get("keys", []):
        if key["kid"] == kid:
            rsa_key = key
            break

    if not rsa_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to find matching key",
        )

    return jwt.decode(
        token,
        rsa_key,
        algorithms=["RS256"],
        audience=settings.auth_audience,
        issuer=settings.auth_issuer,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security_scheme),
) -> CurrentUser:
    """Validate JWT and extract the current user."""
    if not settings.auth_enabled:
        return CurrentUser(
            sub="dev-user",
            name="Development User",
            email="dev@localhost",
            tenant_id="dev-tenant",
            roles=["admin"],
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    try:
        jwks = await _get_jwks()
        payload = _decode_token(credentials.credentials, jwks)
    except JWTError as e:
        logger.warning("jwt_validation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from e

    return CurrentUser(
        sub=payload.get("sub", ""),
        name=payload.get("name", ""),
        email=payload.get("email", payload.get("preferred_username", "")),
        tenant_id=payload.get("tid", ""),
        roles=payload.get("roles", []),
    )
