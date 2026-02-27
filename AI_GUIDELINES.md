# AI_GUIDELINES.md
## Azure Enterprise Cost Optimization Platform

Build and operate a secure, multi-tenant Azure FinOps platform that continuously discovers savings opportunities, prioritizes actionable recommendations, and supports governed remediation across enterprise subscriptions and tenants.


This document defines strict implementation rules for AI-generated code and architectural decisions.

AI must follow these guidelines when generating code, infrastructure, documentation, or automation.

This is an enterprise-grade multi-tenant Azure FinOps platform.
Not a demo project. Not a prototype. Production-ready standards only.

---

# 1. Architectural Principles

## 1.1 Design Goals

- Multi-tenant ready
- Enterprise secure by default
- Least privilege access
- Observable and auditable
- Modular and extensible
- Idempotent infrastructure
- Production-scale resilience

## 1.2 Control Plane Model

All logic runs in a dedicated Azure control-plane subscription.

Customer subscriptions and tenants are accessed via:

- Management Group RBAC (internal)
- Azure Lighthouse (external / MSP model)

AI must never assume single-subscription architecture.

---

# 2. Security Requirements

## 2.1 Identity

- Use Microsoft Entra ID only
- Use Managed Identity whenever possible
- No hardcoded secrets
- Secrets must be stored in Azure Key Vault
- OAuth2 client credentials flow for backend services
- JWT validation required on all API endpoints

## 2.2 RBAC

Follow least privilege principles:

Read-only roles:
- Reader
- Cost Management Reader
- Resource Graph Reader
- Advisor Reader

Remediation roles must be scoped at resource group level when possible.

Never assign Contributor at subscription scope unless explicitly required.

## 2.3 Tenant Isolation

Every data table must contain:
- tenant_id
- subscription_id

No cross-tenant queries without explicit scoping.

---

# 3. Coding Standards

## 3.1 Backend (Python FastAPI)

- Follow clean architecture principles
- Separate:
  - routers
  - services
  - repositories
  - models
- No business logic inside controllers
- Dependency injection required
- Async-first design
- Proper exception handling
- Structured logging

## 3.2 Logging

All services must log:

- correlation_id
- tenant_id
- subscription_id
- operation_name
- duration_ms
- success/failure

Never log secrets or access tokens.

## 3.3 Error Handling

- Use structured error responses
- Never expose stack traces to client
- Implement retry with exponential backoff for Azure API calls
- Handle 429 (throttling) gracefully

---

# 4. Infrastructure Standards

## 4.1 IaC

Infrastructure must be:

- Bicep or Terraform only
- Idempotent
- Parameterized
- Environment-aware (dev / test / prod)
- No manual portal configuration

## 4.2 Networking

- Private endpoints for:
  - Storage
  - Database
  - Key Vault
- No public access unless explicitly required
- WAF for external API exposure

## 4.3 Encryption

- Encryption at rest (default Azure encryption)
- TLS 1.2+
- Customer-managed keys optional for SaaS model

---

# 5. Data Architecture

## 5.1 Raw vs Curated

Raw layer:
- Store original API JSON responses
- Immutable

Curated layer:
- Normalized schema
- Indexed for reporting
- Optimized for queries

## 5.2 Core Entities

Required entities:

- tenants
- subscriptions
- resources
- costs_daily
- recommendations
- audit_logs

All must include:
- created_at
- updated_at

---

# 6. Rule Engine Guidelines

## 6.1 Rule Design

Each rule must provide:

- rule_id
- category
- description
- estimated_monthly_savings
- confidence_score (0-1)
- risk_level (low / medium / high)
- effort_level (low / medium / high)
- explanation field (human readable)

Rules must be:

- Deterministic
- Testable
- Modular (plug-in architecture)
- Isolated from API layer

## 6.2 Savings Estimation

Savings must:

- Use Azure pricing assumptions
- Be conservative
- Clearly explain calculation logic
- Avoid speculative overestimation

---

# 7. Workflow & Governance

## 7.1 Recommendation Lifecycle

Allowed states:

- open
- approved
- rejected
- executed
- dismissed

State transitions must be validated.

## 7.2 Approval Controls

- High-risk actions require approval
- Automated remediation must support:
  - dry-run mode
  - rollback logic
  - audit logging

---

# 8. Performance & Scalability

AI-generated code must:

- Support 100+ subscriptions
- Handle pagination
- Handle API throttling
- Use batch processing where possible
- Avoid N+1 query patterns

---

# 9. Observability

Must integrate:

- Application Insights
- Metrics for:
  - ingestion duration
  - rule execution time
  - recommendation count
  - savings identified

Health endpoint required:
GET /health

---

# 10. API Standards

All endpoints must:

- Be RESTful
- Use proper HTTP status codes
- Require authentication
- Return structured JSON
- Include pagination for list endpoints

Example:

GET /recommendations?tenant_id=xxx&status=open&page=1&page_size=50

---

# 11. Testing Requirements

AI-generated code must include:

- Unit tests for:
  - rule logic
  - savings calculations
  - state transitions
- Mock Azure API responses
- Minimum 80% coverage for rule engine

---

# 12. Anti-Patterns (Forbidden)

AI must NOT:

- Hardcode subscription IDs
- Store secrets in code
- Use synchronous blocking I/O
- Ignore pagination
- Skip error handling
- Assume single-tenant
- Overestimate savings without evidence
- Grant Contributor at subscription level unnecessarily

---

# 13. Documentation Standards

All generated features must include:

- README update
- API documentation
- Architecture diagram update
- Security impact explanation

---

# 14. AI Prompting Rule

When generating new components, AI must:

1. Explain architectural placement
2. Show folder location
3. Provide implementation code
4. Provide tests
5. Explain security implications
6. Validate multi-tenant compatibility

No partial implementations unless explicitly requested.

---

# 15. Long-Term Direction

This platform is evolving toward:

- Autonomous FinOps engine
- Intelligent anomaly detection
- Predictive cost optimization
- Policy-driven cost governance
- Fully automated remediation with human oversight

All designs must support that evolution.
