from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.middleware.correlation import CorrelationIdMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.routers import health, tenants, subscriptions, resources, costs, ingestion, recommendations


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    yield


app = FastAPI(
    title="AzCops - Azure Cost Optimization Platform",
    description="Enterprise-grade multi-tenant Azure Cost Optimization API",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware (order matters - outermost first)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(tenants.router, prefix=settings.api_prefix)
app.include_router(subscriptions.router, prefix=settings.api_prefix)
app.include_router(resources.router, prefix=settings.api_prefix)
app.include_router(costs.router, prefix=settings.api_prefix)
app.include_router(ingestion.router, prefix=settings.api_prefix)
app.include_router(recommendations.router, prefix=settings.api_prefix)
