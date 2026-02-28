# AzCops — Phase 1 & 2 Completion Summary

> **Status:** Both phases committed and merged to `claude/romantic-hoover`
> **Date:** February 2026
> **Stack:** FastAPI · PostgreSQL · Terraform · Azure SDK (Python)

---

## Phase 1 — Foundation (Weeks 1–4) ✅

### 1.1 Project Scaffolding & Tooling

| File | Purpose |
|------|---------|
| `.gitignore` | Python, Node, Terraform, IDE, secrets exclusions |
| `.editorconfig` | Consistent indentation/encoding across editors |
| `.env.example` | Template for local environment variables |
| `Makefile` | `make dev`, `make test`, `make lint`, `make migrate` |
| `docker-compose.yml` | Local PostgreSQL 16 + API via Docker |
| `src/api/Dockerfile` | Multi-stage production Python image |
| `src/ui/Dockerfile` | Multi-stage production Node image |
| `.claude/launch.json` | Dev server configs: colima, postgres, api, ui |

### 1.2 Core API Foundation (`src/api/app/`)

| Module | File | What It Does |
|--------|------|-------------|
| Config | `core/config.py` | Pydantic-settings — all config from env vars, no hardcoding |
| Database | `core/database.py` | Async SQLAlchemy engine, session factory, transactional session DI |
| Security | `core/security.py` | JWT validation against Entra ID JWKS endpoint, `CurrentUser` dataclass |
| Logging | `core/logging.py` | Structlog JSON logging — every log line carries `correlation_id`, `tenant_id`, `operation_name`, `duration_ms` |
| Dependencies | `core/dependencies.py` | FastAPI DI aliases: `DbSession`, `AuthenticatedUser`, `TenantId` |
| Correlation MW | `middleware/correlation.py` | Injects/propagates `X-Correlation-ID` on every request |
| Request Log MW | `middleware/request_logging.py` | Logs method, path, status code, duration_ms on every request |
| Common Schemas | `schemas/common.py` | `PaginatedResponse[T]`, `ErrorResponse`, `HealthResponse` |
| App entry | `main.py` | FastAPI app wiring — middleware stack, all routers, lifespan |

### 1.3 Database Schema — 6 Core Tables

All tables include `tenant_id` (multi-tenant isolation) and `created_at` / `updated_at` timestamps.

| Table | Key Columns | Notes |
|-------|-------------|-------|
| `tenants` | `id`, `name`, `azure_tenant_id`, `type` (internal/external) | Top-level tenant registry |
| `subscriptions` | `tenant_db_id` FK, `subscription_id`, `display_name`, `billing_scope` | Tenant-scoped |
| `resources` | `subscription_db_id` FK, `resource_id`, `type`, `location`, `tags` JSONB | Discovered via ARG |
| `costs_daily` | `subscription_db_id` FK, `date`, `service_name`, `resource_group`, `cost`, `amortized_cost` | Daily granularity |
| `recommendations` | `resource_db_id` FK, `rule_id`, `category`, `estimated_monthly_savings`, `confidence_score`, `risk_level`, `effort_level`, `status` enum | Status state machine |
| `audit_logs` | `action`, `user`, `target_type`, `target_id`, `metadata` JSONB, `timestamp` | Immutable log |

**Recommendation status transitions:**
```
open → approved → executed
open → rejected → open
open → dismissed → open
approved → rejected
```

**Alembic** configured for async migrations. Run with `make migrate`.

### 1.4 REST API Endpoints (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check — DB connectivity, app version |
| `POST` | `/api/v1/tenants` | Register a new Azure tenant |
| `GET` | `/api/v1/tenants` | List tenants (paginated) |
| `GET` | `/api/v1/tenants/{id}` | Get tenant by ID |
| `PATCH` | `/api/v1/tenants/{id}` | Update tenant |
| `DELETE` | `/api/v1/tenants/{id}` | Delete tenant |
| `POST` | `/api/v1/subscriptions` | Register subscription |
| `GET` | `/api/v1/subscriptions` | List subscriptions (tenant-scoped, paginated) |
| `GET` | `/api/v1/subscriptions/{id}` | Get subscription |
| `PATCH` | `/api/v1/subscriptions/{id}` | Update subscription |
| `DELETE` | `/api/v1/subscriptions/{id}` | Delete subscription |

All list endpoints return `PaginatedResponse[T]` with `page`, `page_size`, `total`, `total_pages`.

### 1.5 Terraform Infrastructure (6 Modules)

| Module | Resources Created | Key Settings |
|--------|------------------|--------------|
| `resource_group` | Azure Resource Group | Parameterised name, location, tags |
| `networking` | VNet (10.0.0.0/16), 4 subnets, NSGs, 3 private DNS zones | Subnets: api, db, storage, app |
| `postgresql` | Azure DB for PostgreSQL Flexible Server v16 | SSL enforced, TLS 1.2+, private endpoint, no public access |
| `keyvault` | Azure Key Vault | Soft delete, purge protection (prod), private endpoint, MI access |
| `storage` | Storage Account + Data Lake Gen2 | HNS enabled, `raw` container, private endpoint, TLS 1.2+ |
| `identity` | User-Assigned Managed Identity | Reader + Cost Management Reader at subscription scope |

Dev environment at `infra/terraform/environments/dev/` — compose all modules with B-tier sizing.

### 1.6 Tests

| File | Tests | Coverage |
|------|-------|---------|
| `tests/conftest.py` | Fixtures | Async SQLite in-memory DB, TestClient, mock auth bypass |
| `tests/test_health.py` | 4 | Health endpoint fields, status, version |
| `tests/test_tenants.py` | ~15 | CRUD operations, conflict detection, pagination |
| `tests/test_subscriptions.py` | ~15 | CRUD, tenant scoping, pagination |
| `tests/test_models.py` | ~10 | Enum validation, status transitions |

---

## Phase 2 — Data Ingestion (Weeks 5–8) ✅

### 2.1 Base Connector Layer (`src/ingestion/connectors/base.py`)

The foundation all 4 connectors build on:

| Feature | Implementation |
|---------|---------------|
| Token management | `AzureHttpClient` — caches token, refreshes 60s before expiry |
| Retry logic | Up to 5 attempts, exponential backoff 1s → 60s max |
| 429 Throttle | Reads `Retry-After` header, sleeps exact duration before retry |
| Transient errors | 500, 502, 503, 504 retried with backoff |
| Network errors | `ConnectError`, `TimeoutException` retried |
| Pagination | `paginate()` — auto-follows `nextLink` across all pages |
| Logging | Every request logs: method, URL, status, `duration_ms`, `attempt`, `tenant_id` |
| Multi-tenant | `ConnectorContext` carries `tenant_id`, `subscription_id`, `correlation_id` |

### 2.2 Resource Graph Connector

**File:** `src/ingestion/connectors/resource_graph/`

| Component | Detail |
|-----------|--------|
| API | `POST /providers/Microsoft.ResourceGraph/resources?api-version=2022-10-01` |
| Pagination | `$skipToken` — 1,000 records per page |
| `collect()` | Full inventory for one subscription |
| `collect_waste_candidates()` | 5 parallel KQL queries (asyncio.gather) |
| `collect_rightsizing_candidates()` | 3 parallel KQL queries |

**KQL Query Library (`queries.py`):**

| Query Constant | Purpose |
|----------------|---------|
| `ALL_RESOURCES` | Complete inventory snapshot |
| `UNATTACHED_DISKS` | `diskState == Unattached` |
| `ORPHANED_PUBLIC_IPS` | No `ipConfiguration` or `natGateway` |
| `ORPHANED_NICS` | No `virtualMachine` association |
| `STALE_SNAPSHOTS` | Created > 90 days ago |
| `ALL_VMS` | VMs with size, OS type, power state |
| `APP_SERVICE_PLANS` | With SKU tier and worker count |
| `SQL_DATABASES` | With DTU/vCore SKU details |
| `MISSING_COST_CENTER_TAG` | Resources without `cost-center` tag |

**Mapper** (`mapper.py`): coerces tags (JSON string → dict), normalises type/location/resourceGroup to lowercase.

### 2.3 Cost Management Connector

**File:** `src/ingestion/connectors/cost_management/`

| Feature | Detail |
|---------|--------|
| API | `POST /{scope}/providers/Microsoft.CostManagement/query?api-version=2023-11-01` |
| Cost types | `ActualCost` + `AmortizedCost` fetched in parallel |
| Grouping | `ResourceGroupName` + `ServiceName` + `MeterCategory` |
| Date parsing | Handles `YYYYMMDD` integer and `YYYY-MM-DD` string formats |
| Merge | Amortized cost matched by (resource_group, service_name, date) and merged onto actual records |
| `collect()` | Yesterday's costs (single day) |
| `collect_range()` | Custom date range |

### 2.4 Advisor Connector

**File:** `src/ingestion/connectors/advisor/`

| Feature | Detail |
|---------|--------|
| API | `GET /subscriptions/{sub}/providers/Microsoft.Advisor/recommendations?$filter=Category eq 'Cost'` |
| Pagination | Auto via `nextLink` |
| Savings extraction | `savingsAmount` → `annualSavingsAmount ÷ 12` → impact-based fallback (High=500, Medium=100, Low=20) |
| Confidence scoring | High=0.9, Medium=0.7, Low=0.5 |

### 2.5 Monitor Metrics Connector

**File:** `src/ingestion/connectors/monitor/`

| Feature | Detail |
|---------|--------|
| API | `GET /{resourceId}/providers/microsoft.insights/metrics?api-version=2023-10-01` |
| Metrics | `Percentage CPU` + `Available Memory Bytes` |
| Lookback | 14 days, 1-hour granularity |
| Stats | avg, max, min, p95 per metric per VM |
| Concurrency | All VMs queried in parallel; individual VM errors are isolated |
| Mapper | `is_underutilised_vm()` — flags CPU < 10% avg and memory pressure |

### 2.6 Orchestrator (`src/ingestion/orchestration/orchestrator.py`)

| Feature | Detail |
|---------|--------|
| Concurrency | `asyncio.Semaphore(10)` — max 10 subscriptions in parallel |
| Per-subscription flow | ARG → Cost Mgmt → Advisor → Monitor (sequential within sub) |
| Raw storage | JSON snapshot written before DB upsert |
| DB upsert | `ON CONFLICT DO UPDATE` — idempotent, safe to re-run |
| Error isolation | One subscription failure does not abort other subscriptions |
| Result object | `TenantIngestionResult` — processed count, failed count, totals |

### 2.7 Raw Storage (`src/ingestion/orchestration/raw_storage.py`)

| Mode | Storage Location | Path Pattern |
|------|-----------------|--------------|
| Azure (configured) | Data Lake Gen2 | `abfss://raw@account.dfs.core.windows.net/{tenant}/{connector}/YYYY/MM/DD/{sub}.json` |
| Local (dev fallback) | `data/raw/` | `data/raw/{tenant}/{connector}/YYYY/MM/DD/{sub}.json` |

All snapshots are immutable — upsert never modifies raw layer.

### 2.8 Scheduler (`src/ingestion/orchestration/scheduler.py`)

| Job | Trigger | What |
|-----|---------|------|
| `run_full_ingestion()` | Daily 02:00 UTC | All connectors for all tenants/subscriptions |
| `run_incremental_cost_ingestion()` | Hourly | Cost Management only for near-real-time visibility |

Runs as Azure Container App Job or standalone: `python -m ingestion.orchestration.scheduler [full|incremental]`

### 2.9 Phase 2 API Additions

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/resources` | Paginated resources with filters (type, location, rg, subscription) |
| `GET` | `/api/v1/costs` | Paginated daily cost records with date range filters |
| `GET` | `/api/v1/costs/summary` | 30-day summary: total cost + by-service breakdown + daily trend |
| `POST` | `/api/v1/ingestion/trigger` | Async ingestion trigger — returns `run_id` immediately (202) |
| `GET` | `/api/v1/ingestion/status/{run_id}` | Poll ingestion run status |

### 2.10 Connector Unit Tests

| Test File | Tests | What's Covered |
|-----------|-------|---------------|
| `resource_graph/tests/test_connector.py` | ~12 | collect, pagination, parallel queries, mapper (tag coercion, null safety) |
| `cost_management/tests/test_connector.py` | ~10 | collect, amortized merge, date parsing, mapper |
| `advisor/tests/test_connector.py` | ~10 | collect, savings extraction (3 paths), confidence mapping, mapper |
| `monitor/tests/test_connector.py` | ~10 | collect, VM error isolation, stats (avg/p95/min/max), mapper flags |

All Azure API calls mocked with `AsyncMock` — no real Azure credentials needed to run tests.

---

## File Count Summary

| Layer | `.py` files | `.tf` files | Test files |
|-------|-------------|-------------|-----------|
| API (`src/api/`) | 34 | — | 5 |
| Ingestion (`src/ingestion/`) | 18 | — | 4 |
| Infrastructure (`infra/`) | — | 21 | — |
| **Total** | **52** | **21** | **9** |

---

## What Is NOT Yet Built (Phase 3+)

| Feature | Phase |
|---------|-------|
| Rule Engine (10 rules, scoring) | Phase 3 |
| Recommendation CRUD APIs | Phase 3 |
| Next.js Dashboard | Phase 3 |
| CSV export | Phase 3 |
| Approval workflow | Phase 4 |
| Remediation runbooks | Phase 4 |
| ITSM integration (ServiceNow, Jira) | Phase 4 |
| ML anomaly detection | Future |
| Predictive forecasting | Future |
