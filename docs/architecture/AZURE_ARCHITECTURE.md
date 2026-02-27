# AzCops — Azure Architecture Design

> **Version:** 1.0 · February 2026
> **Model:** Enterprise multi-tenant FinOps control plane
> **Patterns:** Hub-and-spoke · Private endpoints · Managed Identity · FinOps Framework

---

## 1. High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AzCops CONTROL PLANE TENANT                          │
│                                                                             │
│   ┌──────────────┐    ┌──────────────────────────────────────────────────┐  │
│   │   Users /    │    │              Azure Virtual Network               │  │
│   │  FinOps Team │    │           (10.0.0.0/16)  Private                 │  │
│   │  Architects  │    │  ┌───────────┐  ┌───────────┐  ┌────────────────┐│  │
│   └──────┬───────┘    │  │ API Snet  │  │  DB Snet  │  │ Storage Snet   ││  │
│          │            │  │10.0.1.0/24│  │10.0.2.0/24│  │  10.0.3.0/24   ││  │
│          ▼            │  └────┬──────┘  └────┬──────┘  └───────┬────────┘│  │
│   ┌──────────────┐    │       │              │                 │         │  │
│   │  App Gateway │────┼───────▼──────────────▼─────────────────▼─────────┤  │
│   │    + WAF     │    │  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │  │
│   └──────────────┘    │  │FastAPI   │  │PostgreSQL│  │ Data Lake Gen2 │  │  │
│                       │  │Container │  │Flex Srv  │  │  (raw layer)   │  │  │
│   ┌──────────────┐    │  │App       │  │ v16      │  │                │  │  │
│   │  Entra ID    │    │  └──────────┘  └──────────┘  └────────────────┘  │  │
│   │  (Auth)      │    │                                                  │  │
│   └──────────────┘    │  ┌──────────┐  ┌──────────────────────────────┐  │  │
│                       │  │Key Vault │  │  Container Apps Jobs         │  │  │
│   ┌──────────────┐    │  │(secrets) │  │  (ingestion scheduler)       │  │  │
│   │  Managed     │    │  └──────────┘  └──────────────────────────────┘  │  │
│   │  Identity    │    └──────────────────────────────────────────────────┘  │
│   └──────────────┘                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
         │  Azure Lighthouse / Management Group RBAC
         ▼
┌─────────────────────────────────────────────────────────┐
│              CUSTOMER / MANAGED TENANTS                 │
│                                                         │
│  ┌─────────────────┐    ┌─────────────────┐             │
│  │  Tenant A       │    │  Tenant B (MSP) │   ...       │
│  │  ├─ Sub-001     │    │  ├─ Sub-010     │             │
│  │  ├─ Sub-002     │    │  ├─ Sub-011     │             │
│  │  └─ Sub-003     │    │  └─ Sub-012     │             │
│  └─────────────────┘    └─────────────────┘             │
│                                                         │
│  APIs consumed (read-only):                             │
│  • Azure Resource Graph                                 │
│  • Cost Management Query API                            │
│  • Azure Advisor                                        │
│  • Azure Monitor Metrics                                │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Networking Design

### 2.1 Virtual Network Layout

```
VNet: azcops-dev-vnet (10.0.0.0/16)
│
├── Subnet: api     (10.0.1.0/24)   ← Container App Environment
│   └── NSG: Allow 443 inbound from App Gateway only
│
├── Subnet: db      (10.0.2.0/24)   ← PostgreSQL VNet integration
│   └── NSG: Allow 5432 inbound from api subnet only
│   └── Delegation: Microsoft.DBforPostgreSQL/flexibleServers
│
├── Subnet: storage (10.0.3.0/24)   ← Private endpoints for Storage + Key Vault
│   └── NSG: Deny all inbound; allow service traffic only
│
└── Subnet: app     (10.0.4.0/24)   ← Container Apps Jobs (ingestion)
    └── NSG: Allow outbound to Azure APIs only
    └── Delegation: Microsoft.App/environments
```

### 2.2 Private Endpoints

| Resource                   | Private DNS Zone                          | Subnet  |
| -------------------------- | ----------------------------------------- | ------- |
| PostgreSQL Flexible Server | `privatelink.postgres.database.azure.com` | db      |
| Azure Key Vault            | `privatelink.vaultcore.azure.net`         | storage |
| Data Lake Gen2             | `privatelink.dfs.core.windows.net`        | storage |

All services have `public_network_access = Disabled`. Zero internet exposure.

### 2.3 Inbound Traffic Flow

```
Internet
    │
    ▼ HTTPS (443)
┌───────────────────────────────┐
│  Application Gateway + WAF    │  ← TLS termination, WAF rules, DDoS protection
│  (Public IP — only entry)     │
└───────────────┬───────────────┘
                │ HTTP (internal)
                ▼
┌───────────────────────────────┐
│  FastAPI on Container Apps    │  ← JWT validation (Entra ID)
│  (api subnet — private only)  │  ← Tenant context middleware
└───────────────────────────────┘
```

---

## 3. Identity & Access Model

### 3.1 Human Access (North-South)

```
User Browser
    │
    ├──► Microsoft Entra ID (Authentication)
    │         └── Returns JWT with claims: sub, tid, roles
    │
    └──► App Gateway → FastAPI
              └── JWT validated against Entra JWKS endpoint
              └── tenant_id extracted from `tid` claim
              └── roles checked per endpoint
```

### 3.2 Service-to-Service (East-West)

```
Container App / Container App Job
    │
    ├── User-Assigned Managed Identity (no secrets, no passwords)
    │         ├── Reader role → Customer subscriptions
    │         ├── Cost Management Reader role → Customer subscriptions
    │         ├── Resource Graph Reader role → Customer subscriptions
    │         └── Advisor Reader role → Customer subscriptions
    │
    ├── Key Vault (secrets access via MI)
    │         └── Database connection strings
    │         └── App config secrets
    │
    └── Data Lake Gen2 (Storage Blob Data Contributor via MI)
              └── Write raw API snapshots
```

### 3.3 RBAC Assignments per Scope

| Role                          | Scope                           | Assigned To      | Purpose             |
| ----------------------------- | ------------------------------- | ---------------- | ------------------- |
| Reader                        | Management Group / Subscription | Managed Identity | Resource inventory  |
| Cost Management Reader        | Subscription                    | Managed Identity | Cost data access    |
| Storage Blob Data Contributor | Storage Account                 | Managed Identity | Raw data writes     |
| Key Vault Secrets User        | Key Vault                       | Managed Identity | Secret reads        |
| Key Vault Secrets Officer     | Key Vault                       | Deployer SP      | CI/CD secret writes |

**Principle:** Never assign `Contributor` at subscription scope. Least privilege always.

---

## 4. Multi-Tenant Connectivity

### 4.1 Internal Enterprise Model

```
Control Plane MI
    │
    └──► Management Group (scope)
              ├── Reader role assigned
              ├── Cost Management Reader role assigned
              └── All subscriptions under MG inherit access

No cross-tenant trust needed — single Azure AD tenant.
```

### 4.2 External MSP Model (Azure Lighthouse)

```
Customer Tenant
    │
    └──► Azure Lighthouse Delegation
              └── Managed by: AzCops Control Plane Tenant
              └── Roles delegated:
                    • Reader
                    • Cost Management Reader
              └── Customer can revoke at any time

Control Plane
    └──► Queries customer APIs using delegated access
    └──► All data stored with tenant_id isolation in DB
    └──► Optional: per-customer encryption key in Key Vault
```

### 4.3 Tenant Isolation in Database

Every table enforces tenant isolation via `tenant_id` column:

```sql
-- Example: query always scoped to tenant
SELECT * FROM resources
WHERE tenant_id = :tenant_id       -- always required
  AND subscription_db_id = :sub_id -- further scoped
  AND type = 'microsoft.compute/disks';

-- No cross-tenant queries permitted
-- tenant_id extracted from JWT `tid` claim — not from user input
```

---

## 5. Data Architecture

### 5.1 Two-Layer Storage

```
Azure APIs (Cost Mgmt, ARG, Advisor, Monitor)
    │
    ▼ Raw ingest (immutable)
┌─────────────────────────────────────────────────────┐
│  Azure Data Lake Gen2  (raw layer)                  │
│                                                     │
│  Path: {tenant}/{connector}/YYYY/MM/DD/{sub}.json   │
│  Format: JSON (original API response + metadata)    │
│  Retention: 90 days (configurable)                  │
│  Access: write-once, never modified                 │
└──────────────────────────┬──────────────────────────┘
                           │ Transform & normalise
                           ▼
┌─────────────────────────────────────────────────────┐
│  Azure Database for PostgreSQL (curated layer)      │
│                                                     │
│  Tables: tenants, subscriptions, resources,         │
│          costs_daily, recommendations, audit_logs   │
│  Indexed for queries, reporting, rule engine        │
│  Upsert idempotent (safe to re-run ingestion)       │
└─────────────────────────────────────────────────────┘
```

### 5.2 Ingestion Data Flow

```
[Container App Job — Scheduler]
    │
    ├── For each active tenant
    │       └── For each subscription (max 10 parallel)
    │               │
    │               ├── 1. Resource Graph → raw/  → resources table
    │               ├── 2. Cost Mgmt     → raw/  → costs_daily table
    │               ├── 3. Advisor       → raw/  (rules engine maps later)
    │               └── 4. Monitor       → raw/  (rules engine maps later)
    │
    └── Orchestrator returns TenantIngestionResult
```

### 5.3 Data Retention Policy

| Layer              | Retention                         | Location       |
| ------------------ | --------------------------------- | -------------- |
| Raw JSON snapshots | 90 days                           | Data Lake Gen2 |
| Curated cost data  | 13 months (rolling)               | PostgreSQL     |
| Curated resources  | Latest snapshot + 30 days history | PostgreSQL     |
| Recommendations    | Indefinite (lifecycle tracked)    | PostgreSQL     |
| Audit logs         | 7 years (compliance)              | PostgreSQL     |

---

## 6. Application Architecture

### 6.1 FastAPI Clean Architecture

```
HTTP Request
    │
    ▼
┌─────────────────────────────────────────┐
│  Middleware Stack                       │
│  1. CorrelationIdMiddleware             │  Injects X-Correlation-ID
│  2. RequestLoggingMiddleware            │  Logs duration_ms, status
│  3. CORSMiddleware                      │  Entra-authenticated origins
└──────────────────────┬──────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────┐
│  Router (routers/)                      │  HTTP → validated Pydantic schema
│  • No business logic here               │
│  • Calls Service layer only             │
└──────────────────────┬──────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────┐
│  Service (services/)                    │  Business logic, validation
│  • Raises HTTPException on errors       │
│  • Calls Repository layer only          │
│  • Logs with operation_name             │
└──────────────────────┬──────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────┐
│  Repository (repositories/)             │  DB queries only, tenant-scoped
│  • BaseRepository[T] generic CRUD       │
│  • All queries include tenant_id        │
│  • Returns ORM models                   │
└──────────────────────┬──────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────┐
│  PostgreSQL (async SQLAlchemy)          │
└─────────────────────────────────────────┘
```

### 6.2 API Versioning Strategy

- All endpoints under `/api/v1/`
- Future: `/api/v2/` added alongside v1 (no breaking changes)
- OpenAPI docs auto-generated at `/docs` (Swagger UI)
- ReDoc at `/redoc`

---

## 7. Security Design

### 7.1 Security Controls by Layer

| Layer             | Control          | Implementation                                      |
| ----------------- | ---------------- | --------------------------------------------------- |
| Network perimeter | WAF + DDoS       | App Gateway WAF v2 (OWASP rules)                    |
| API auth          | JWT validation   | Entra ID JWKS, RS256, audience + issuer checks      |
| API authz         | RBAC             | Roles extracted from JWT `roles` claim              |
| Service auth      | Managed Identity | No secrets, no passwords for service-to-service     |
| Secrets           | Key Vault        | All secrets in KV; never in code or env files       |
| Data encryption   | At rest          | Azure default encryption (AES-256)                  |
| Data encryption   | In transit       | TLS 1.2+ enforced on all services                   |
| Multi-tenancy     | Row-level        | `tenant_id` on every DB table, extracted from JWT   |
| Audit             | Immutable log    | `audit_logs` table, every action recorded           |
| Remediation       | Approval gate    | High-risk actions require approval before execution |

### 7.2 Secrets Management

```
Key Vault: azcops-dev-kv
│
├── Secret: postgresql-connection-string
│       └── Referenced by Container App via MI (no env var)
├── Secret: storage-account-key (optional — MI preferred)
└── Secret: api-client-secret (if needed for specific integrations)

All secrets:
  - Never logged (structlog filters checked)
  - Never in git (gitignore covers .env, *.key, *.pem)
  - Rotated via Key Vault policies
  - Accessed by MI only (no human access in prod)
```

### 7.3 Threat Model Summary

| Threat                                  | Mitigation                                             |
| --------------------------------------- | ------------------------------------------------------ |
| Credential theft                        | Managed Identity — no static credentials exist         |
| Cross-tenant data leak                  | `tenant_id` enforced at DB + JWT layer                 |
| Injection attacks                       | Pydantic validation + parameterised SQLAlchemy queries |
| Privilege escalation                    | Least-privilege RBAC; no Contributor at sub scope      |
| Data exfiltration                       | Private endpoints; no public storage access            |
| Unauthorised API access                 | JWT + audience/issuer validation on every endpoint     |
| Prompt injection (if AI features added) | Human approval gates before any remediation            |

---

## 8. Observability Design

### 8.1 Logging Strategy

```
Every log entry contains:
  • correlation_id   — traces a request across all services
  • tenant_id        — identifies which customer
  • subscription_id  — identifies which Azure subscription
  • operation_name   — e.g. "resource_graph.all_resources"
  • duration_ms      — performance tracking
  • success/failure  — outcome
```

Shipped to: **Application Insights** (via OpenTelemetry SDK — Phase 3+)

### 8.2 Key Metrics to Track

| Metric                               | Description                 | Alert Threshold |
| ------------------------------------ | --------------------------- | --------------- |
| `ingestion.duration_ms`              | Full ingestion job duration | > 30 min        |
| `ingestion.subscriptions_failed`     | Failed subscription count   | > 0             |
| `rule_engine.rules_evaluated`        | Rules run per cycle         | < 10            |
| `recommendations.savings_identified` | Total monthly savings found | Informational   |
| `api.request_duration_ms`            | p95 API latency             | > 2000ms        |
| `api.error_rate`                     | 5xx rate                    | > 1%            |
| `cost_management.throttle_429`       | Azure API throttle events   | > 5/hour        |

### 8.3 Health Endpoint

```
GET /health
→ 200 { "status": "healthy", "version": "0.1.0", "database": "connected" }
→ 207 { "status": "degraded", "database": "disconnected" }
```

Used by App Gateway health probes and Container App liveness checks.

---

## 9. Deployment Architecture

### 9.1 Environments

| Environment | Purpose                | Sizing                             | Access     |
| ----------- | ---------------------- | ---------------------------------- | ---------- |
| `dev`       | Local development + CI | B_Standard_B1ms PG, LRS storage    | Developers |
| `test`      | Integration testing    | B_Standard_B2ms PG, LRS storage    | CI/CD      |
| `prod`      | Live workloads         | GP_Standard_D4s_v3 PG, ZRS storage | Ops only   |

### 9.2 CI/CD Pipeline (infra/pipelines/)

```
Git Push → PR
    │
    ├── Lint (ruff, mypy, prettier, terraform fmt)
    ├── Unit Tests (pytest, no Azure credentials)
    ├── terraform plan (dev environment)
    └── Build Docker images (multi-stage)
            │
            ▼ Merge to main
    ├── terraform apply (dev auto, prod manual approval)
    ├── Docker push to Azure Container Registry
    └── Container App revision deploy (zero-downtime)
```

### 9.3 Container App Configuration

| App                            | Replicas                 | CPU | Memory | Trigger        |
| ------------------------------ | ------------------------ | --- | ------ | -------------- |
| `azcops-api`                   | 1–5 (auto-scale on HTTP) | 0.5 | 1Gi    | HTTP           |
| `azcops-ingestion-full`        | 1                        | 2.0 | 4Gi    | Cron 0 2 * * * |
| `azcops-ingestion-incremental` | 1                        | 1.0 | 2Gi    | Cron 0 * * * * |

---

## 10. Phase 3 Architecture Additions (Planned)

### 10.1 Rule Engine

```
src/engine/
├── rules/
│   ├── base.py              ← Abstract BaseRule (evaluate → RuleResult)
│   ├── registry.py          ← Plugin registry, auto-discover rules
│   ├── waste/
│   │   ├── unattached_disks.py
│   │   ├── orphaned_ips.py
│   │   ├── orphaned_nics.py
│   │   └── stale_snapshots.py
│   ├── rightsizing/
│   │   ├── underutilised_vms.py
│   │   ├── app_service_plan.py
│   │   └── sql_dtu.py
│   ├── rate/
│   │   ├── reserved_instance_gap.py
│   │   └── savings_plan.py
│   └── governance/
│       └── missing_cost_center_tag.py
└── scoring/
    └── scorer.py            ← priority = savings × confidence ÷ risk_weight
```

### 10.2 Next.js Dashboard

```
src/ui/src/
├── app/
│   ├── (auth)/login/        ← MSAL.js + Entra ID login
│   ├── dashboard/           ← Overview: spend, savings, top recs
│   ├── cost-explorer/       ← Charts: by service, by RG, trend
│   ├── recommendations/     ← List with filters, approve/dismiss
│   └── settings/
│       ├── tenants/         ← Register tenants
│       └── subscriptions/   ← Manage subscriptions
├── components/
│   ├── charts/              ← Recharts cost trend, pie charts
│   ├── recommendations/     ← Table, status badges, action buttons
│   └── layout/              ← Sidebar, header, breadcrumb
└── lib/
    ├── api.ts               ← Typed API client (fetch wrappers)
    └── auth.ts              ← MSAL.js configuration
```

---

## 11. Architecture Decision Records (ADRs)

| ADR     | Decision                        | Rationale                                                     |
| ------- | ------------------------------- | ------------------------------------------------------------- |
| ADR-001 | FastAPI over .NET               | Python Azure SDK maturity; async-first; team velocity         |
| ADR-002 | PostgreSQL over Azure SQL       | Open-source; asyncpg support; JSONB for tags/metadata         |
| ADR-003 | Terraform over Bicep            | Multi-environment state management; team familiarity          |
| ADR-004 | Container Apps over AKS         | Lower operational overhead; auto-scaling; job support         |
| ADR-005 | Managed Identity over SPs       | No credential rotation; no secret leakage risk                |
| ADR-006 | Two-layer storage (DL + PG)     | Raw immutability for audit; curated for fast queries          |
| ADR-007 | tenant_id on every table        | Row-level isolation without RLS complexity                    |
| ADR-008 | Async-first Python              | 100+ subscriptions; I/O-bound workload; throughput            |
| ADR-009 | nextLink + skipToken pagination | Azure API standard; avoids data loss on large datasets        |
| ADR-010 | Approval gate for remediation   | Regulatory compliance; prevents unintended production changes |
