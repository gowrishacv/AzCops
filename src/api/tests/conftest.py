"""
Shared test fixtures for the AzCops API test suite.

Uses aiosqlite with an in-memory SQLite database so tests run fast
and without any external infrastructure.  PostgreSQL-specific column
types (UUID, JSONB) are compiled to their SQLite equivalents via
custom DDL compilers registered at import time.

IMPORTANT: We deliberately leave DATABASE_URL as the default PostgreSQL
URL.  The module-level engine in ``app.core.database`` is never actually
*connected* during tests because every code-path goes through the
overridden ``get_db_session`` dependency (or the patched
``async_session_factory`` for the health router).  This avoids the
``pool_size`` / ``max_overflow`` TypeError that occurs when SQLAlchemy
tries to create a SQLite engine with PostgreSQL-only pool arguments.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

# ---------------------------------------------------------------------------
# Register SQLite-compatible DDL compilers for PostgreSQL-only column types.
# These must be registered before any ``create_all()`` call.
# ---------------------------------------------------------------------------


@compiles(UUID, "sqlite")
def _compile_uuid_for_sqlite(type_, compiler, **kw):
    """Render PostgreSQL UUID as CHAR(32) in SQLite."""
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(type_, compiler, **kw):
    """Render PostgreSQL JSONB as TEXT (JSON stored as string) in SQLite."""
    return "TEXT"


# ---------------------------------------------------------------------------
# Override auth setting BEFORE any application code is imported.
# DATABASE_URL is left at its default (PostgreSQL) -- see module docstring.
# ---------------------------------------------------------------------------

os.environ["AUTH_ENABLED"] = "false"

# Now it is safe to import application modules.
from app.core.config import settings  # noqa: E402
from app.core.database import get_db_session  # noqa: E402
from app.core.security import CurrentUser, get_current_user  # noqa: E402

# Import ALL models so SQLAlchemy metadata is fully populated before create_all().
from app.models import (  # noqa: E402, F401
    AuditLog,
    Base,
    CostDaily,
    Recommendation,
    Resource,
    Subscription,
    Tenant,
)
from app.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# Test database engine & session factory  (SQLite in-memory)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

test_session_factory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@event.listens_for(test_engine.sync_engine, "connect")
def _enable_sqlite_fks(dbapi_connection, connection_record):
    """Enable foreign-key enforcement on every new SQLite connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ---------------------------------------------------------------------------
# Mock authenticated user
# ---------------------------------------------------------------------------
TEST_TENANT_ID = "test-tenant"

mock_user = CurrentUser(
    sub="test-user-id",
    name="Test User",
    email="test@example.com",
    tenant_id=TEST_TENANT_ID,
    roles=["admin"],
)


async def _override_get_current_user() -> CurrentUser:
    return mock_user


async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def _setup_database():
    """Create all tables before each test and tear them down after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session for direct DB access in tests."""
    async with test_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture()
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client wired to the FastAPI app with all dependency overrides."""
    app.dependency_overrides[get_db_session] = _override_get_db_session
    app.dependency_overrides[get_current_user] = _override_get_current_user

    # Patch the session factory that the health router uses directly
    # (it doesn't go through dependency injection).
    with patch("app.routers.health.async_session_factory", test_session_factory):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client

    app.dependency_overrides.clear()


@pytest.fixture()
def override_settings():
    """Expose the live Settings instance for assertion in tests."""
    return settings
