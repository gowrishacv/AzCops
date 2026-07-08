Works Council Statement Regarding Current Rumors About Further Job Reductions

Dear colleagues,

Over the past few days, many of you have approached the Works Council with questions, concerns, and information regarding rumors that, in addition to the currently ongoing voluntary redundancy program, further positions may be eliminated and that lists of potentially affected employees are already being prepared.

We take these reports very seriously.

At this point, however, the Works Council has not received any official confirmation or information from management regarding such measures. Therefore, we will not present rumors or speculation as established facts.
At the same time, we want to make our position clear: If management is considering measures that go beyond the current voluntary program and may have an impact on employees, we expect the Works Council to be informed at an early stage and in a comprehensive manner. This is consistent with our statutory information and participation rights under German labor law.

Our commitment is clear:
•	We are closely monitoring the current situation.
•	We are in dialogue with management and will actively seek clarification where necessary.
•	We will consistently exercise our information, consultation, and co-determination rights.
•	We will keep employees informed as soon as reliable information becomes available.
•	
We understand that rumors and uncertainty can be unsettling. For that reason, we are committed to communicating responsibly and sharing only verified information.

We expect management to communicate openly and transparently with both the Works Council and employees. Especially during periods of organizational change, timely communication and early involvement are essential to maintaining trust and avoiding unnecessary uncertainty. If further personnel measures are being considered, we expect these not to become known through rumors or unofficial channels, but to be communicated through a transparent and respectful process that appropriately involves the Works Council.

If you have questions, concerns, or relevant information, please feel free to contact the Works Council in confidence. Any information you share helps us better understand developments and raise the appropriate questions with management.
We will keep you informed as soon as reliable and confirmed information becomes available.

Your Works Council

# Azure Enterprise Cost Optimization Platform

An enterprise-grade, multi-tenant Azure Cost Optimization platform designed for FinOps teams, Cloud Architects, and Managed Service Providers.

This solution supports multiple Azure tenants and subscriptions, provides automated cost optimization insights, and enables governed remediation workflows.

## Development Guidelines

Please review the AI contribution policy before submitting AI-assisted changes:

- [AI Guidelines](./AI_GUIDELINES.md)

All AI-assisted pull requests should include disclosure details as defined in the PR template.

---

# 1. Vision

Build a centralized control plane that:

- Connects multiple Azure tenants and subscriptions
- Aggregates cost, inventory, and utilization data
- Generates actionable optimization recommendations
- Enables governed remediation workflows
- Supports both internal enterprise and external SaaS models
- Aligns with FinOps operating principles

---

# 2. Core Capabilities

## Multi-Tenant & Multi-Subscription Management
- Management Group support
- Azure Lighthouse for cross-tenant access
- Delegated RBAC with least privilege

## Data Collection
- Azure Cost Management Query API
- Azure Consumption / Usage APIs
- Azure Resource Graph
- Azure Advisor API
- Azure Monitor Metrics
- Budget and Cost Exports (optional)

## Optimization Intelligence
- Underutilized VMs and compute
- Orphaned resources (disks, IPs, NICs)
- SQL, Cosmos, App Service right-sizing
- Reserved Instance & Savings Plan coverage
- Spot VM candidate identification
- Tag compliance & governance gaps
- Budget and anomaly detection

## Workflow & Remediation
- Approval workflow
- Owner assignment
- Exception tracking
- ITSM integration (ServiceNow, Jira, Azure DevOps)
- Automated remediation with guardrails
- Full audit logging

---

# 3. High-Level Architecture

## Control Plane
- Hosted in a dedicated Azure subscription
- Centralized data ingestion and rule engine
- API + UI layer

## Data Ingestion
- Azure Functions or Container Apps Jobs
- Scheduled ingestion (daily / hourly)
- Service Bus for orchestration (optional)

## Storage
- Raw: Azure Data Lake Gen2
- Curated: Azure SQL or PostgreSQL
- Analytics: Synapse / Fabric / Databricks (optional)

## Application Layer
- Backend API: FastAPI (Python) or .NET Web API
- Frontend: React / Next.js / Power BI Embedded
- Auth: Microsoft Entra ID
- Secrets: Azure Key Vault
- Identity: Managed Identities

---

# 4. Multi-Tenant Connectivity

## Internal Enterprise

- Assign Reader / Cost Management Reader at Management Group scope
- Centralized Service Principal or Managed Identity
- Use Resource Graph for cross-subscription inventory

## External Customers (MSP Model)

- Azure Lighthouse delegation
- Control plane in managing tenant
- Tenant isolation in database (tenant_id column required)
- Optional per-customer encryption keys

---

# 5. Data Sources & APIs

## Cost Management Query API

Endpoint:
POST https://management.azure.com/{scope}/providers/Microsoft.CostManagement/query?api-version=2023-11-01

Used for:
- Daily cost
- Amortized cost
- Grouping by resource group, service, tag

## Azure Resource Graph

Used for:
- Inventory snapshot
- Tag compliance
- Orphaned resources detection

## Azure Advisor

Used for:
- Built-in cost recommendations
- Impact analysis
- Integration into rule engine

## Azure Monitor Metrics

Used for:
- VM CPU / memory trends
- Right-sizing logic

---

# 6. Data Model (Core Tables)

## tenants
- id
- name
- type (internal / external)

## subscriptions
- id
- tenant_id
- display_name
- billing_scope

## resources
- id
- subscription_id
- resource_id
- type
- location
- tags
- last_seen

## costs_daily
- id
- subscription_id
- date
- service_name
- resource_group
- cost
- amortized_cost

## recommendations
- id
- resource_id
- rule_id
- category
- estimated_monthly_savings
- confidence_score
- risk_level
- effort_level
- status (open, approved, executed, dismissed)
- owner
- created_at

## audit_logs
- id
- action
- user
- timestamp
- metadata

---

# 7. Rule Engine Strategy

Each rule produces:

- Estimated monthly savings
- Confidence score
- Risk level
- Effort estimate
- Owner
- SLA target

## Example Rule Categories

### Waste Detection
- Unattached managed disks
- Idle public IP addresses
- Orphaned NICs
- Stale snapshots

### Right-Sizing
- VM CPU < 10% for 14 days
- App Service Plan underutilized
- SQL DTU < 20% utilization

### Rate Optimization
- Reserved Instance coverage gap
- Savings Plan opportunities
- Spot VM candidates

### Governance
- Missing cost center tag
- Budget threshold breach
- Anomaly detection on spend spike

---

# 8. Sample Queries & Code

## Resource Graph – Unattached Disks

```bash
az graph query -q "
Resources
| where type =~ 'microsoft.compute/disks'
| extend diskState = tostring(properties.diskState)
| where diskState =~ 'Unattached'
| project name, resourceGroup, subscriptionId, location
"


Advisor Recommendations
import requests
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
token = credential.get_token("https://management.azure.com/.default").token

scope = "/subscriptions/<SUB_ID>"
url = f"https://management.azure.com{scope}/providers/Microsoft.CostManagement/query?api-version=2023-11-01"

payload = {
  "type": "ActualCost",
  "timeframe": "MonthToDate",
  "dataset": {
    "granularity": "Daily",
    "aggregation": {
      "totalCost": {"name": "Cost", "function": "Sum"}
    },
    "grouping": [
      {"type": "Dimension", "name": "ResourceGroupName"}
    ]
  }
}

response = requests.post(
  url,
  headers={
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
  },
  json=payload,
  timeout=60
)

print(response.json())

9. Repository Structure

azure-cost-optimizer/
  docs/
    architecture/
    adr/
    runbooks/
  infra/
    bicep/
    terraform/
    pipelines/
  src/
    api/
      app/
        main.py
        routers/
        services/
        models/
      tests/
    ingestion/
      connectors/
        cost_management/
        resource_graph/
        advisor/
        monitor/
      orchestration/
    engine/
      rules/
      scoring/
    remediation/
      runbooks/
      approvals/
    ui/
  data/
    schemas/
  security/
    threat-model/
  scripts/
  README.md
  
  10. Hosting Options

Internal Enterprise Deployment
	•	Private Endpoints for storage and DB
	•	API behind Application Gateway + WAF
	•	Internal-only access or Entra App Proxy
	•	RBAC scoped to Management Groups

External SaaS Model
	•	Control plane tenant
	•	Azure Lighthouse delegation
	•	Tenant isolation in database
	•	Strong audit logging
	•	Customer-level RBAC

⸻

11. Security Model
	•	Microsoft Entra ID authentication
	•	Managed Identities for service access
	•	Key Vault for secrets
	•	Role-based access control
	•	Audit logging for all actions
	•	Approval workflow before remediation

⸻

12. Project Plan (90-Day Roadmap)

Phase 1 – Foundation (Weeks 1–4)
	•	Control plane subscription
	•	Identity and RBAC setup
	•	Base infrastructure deployment
	•	Database schema

Phase 2 – Data Ingestion (Weeks 5–8)
	•	Resource Graph inventory
	•	Cost Management ingestion
	•	Advisor integration
	•	Daily scheduler

Phase 3 – MVP Rule Engine (Weeks 9–12)
	•	Top 10 cost-saving rules
	•	Savings estimation logic
	•	Basic dashboard
	•	CSV export

Phase 4 – Workflow & Automation (Optional Extension)
	•	Approval flow
	•	Remediation runbooks
	•	Notifications
	•	ITSM integration

⸻

13. Future Enhancements
	•	ML-based anomaly detection
	•	Predictive cost forecasting
	•	Carbon footprint analysis
	•	Multi-cloud support
	•	Executive reporting dashboard
	•	Chargeback / showback engine

⸻

14. FinOps Alignment

Supports:
	•	Visibility
	•	Optimization
	•	Governance
	•	Continuous improvement

Designed for weekly FinOps review cycles and monthly executive reporting.

⸻

License

Enterprise internal use or SaaS extension. Customize based on organization policy.

---

If you want, I can now generate:

- A production-ready `.gitignore`
- A full OpenAPI spec
- A Bicep/Terraform starter
- A backlog in Azure DevOps format
- Or a SaaS multi-customer version with billing model built-in
