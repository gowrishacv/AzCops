#!/usr/bin/env bash
# =============================================================================
# AzCops — Azure Bootstrap Script
# Creates all required Azure identities, roles, and outputs .env values.
#
# PREREQUISITES:
#   brew install azure-cli          # or: https://aka.ms/installazurecli
#   az login                        # sign in with your Azure account
#
# USAGE:
#   chmod +x infra/scripts/bootstrap-spn.sh
#   ./infra/scripts/bootstrap-spn.sh
#
# WHAT IT CREATES:
#   1. App Registration (Entra ID)  → for MSAL UI auth + backend JWT validation
#   2. Service Principal            → for Terraform + ingestion (CI/CD)
#   3. Role assignments             → Reader + Cost Management Reader
#   4. Terraform state storage      → Resource Group + Storage Account
#   5. Prints all .env values       → copy-paste ready
# =============================================================================
set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Configuration (edit these if needed) ──────────────────────────────────────
APP_NAME="${AZCOPS_APP_NAME:-AzCops}"
ENVIRONMENT="${AZCOPS_ENV:-dev}"
LOCATION="${AZCOPS_LOCATION:-westeurope}"
TF_STATE_RG="${APP_NAME}-tfstate-rg"
TF_STATE_SA="azcops${ENVIRONMENT}tfstate$RANDOM"   # must be globally unique
TF_STATE_CONTAINER="tfstate"
REDIRECT_URI="${AZCOPS_REDIRECT_URI:-http://localhost:3000}"

# ── Pre-flight checks ─────────────────────────────────────────────────────────
command -v az >/dev/null 2>&1 || error "Azure CLI not installed. Run: brew install azure-cli"

info "Checking Azure CLI login status..."
ACCOUNT=$(az account show --query '{name:name,id:id,tenantId:tenantId}' -o json 2>/dev/null) \
  || error "Not logged in. Run: az login"

SUBSCRIPTION_ID=$(echo "$ACCOUNT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
TENANT_ID=$(echo "$ACCOUNT"       | python3 -c "import sys,json; print(json.load(sys.stdin)['tenantId'])")
SUB_NAME=$(echo "$ACCOUNT"        | python3 -c "import sys,json; print(json.load(sys.stdin)['name'])")

echo ""
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  AzCops Bootstrap — Subscription: ${SUB_NAME}${NC}"
echo -e "${YELLOW}  Subscription ID : ${SUBSCRIPTION_ID}${NC}"
echo -e "${YELLOW}  Tenant ID       : ${TENANT_ID}${NC}"
echo -e "${YELLOW}  Environment     : ${ENVIRONMENT}${NC}"
echo -e "${YELLOW}  Location        : ${LOCATION}${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo ""
read -rp "  Proceed? [y/N] " CONFIRM
[[ "$CONFIRM" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — App Registration (for MSAL / JWT validation)
# ═══════════════════════════════════════════════════════════════════════════════
info "Step 1/5 — Creating App Registration: ${APP_NAME}..."

EXISTING_APP=$(az ad app list --display-name "$APP_NAME" --query "[0].appId" -o tsv 2>/dev/null)

if [[ -n "$EXISTING_APP" && "$EXISTING_APP" != "None" ]]; then
  warn "App Registration '${APP_NAME}' already exists (appId: ${EXISTING_APP}). Reusing."
  CLIENT_ID="$EXISTING_APP"
else
  CLIENT_ID=$(az ad app create \
    --display-name "$APP_NAME" \
    --sign-in-audience "AzureADMyOrg" \
    --web-redirect-uris "$REDIRECT_URI" "http://localhost:3000/auth/callback" \
    --enable-access-token-issuance true \
    --enable-id-token-issuance true \
    --query appId -o tsv)
  success "App Registration created: ${CLIENT_ID}"

  # Add standard OIDC scopes
  az ad app update \
    --id "$CLIENT_ID" \
    --set "optionalClaims={\"idToken\":[{\"name\":\"email\",\"essential\":false},{\"name\":\"upn\",\"essential\":false}]}" \
    >/dev/null 2>&1 || true
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Service Principal + client secret (for Terraform + ingestion)
# ═══════════════════════════════════════════════════════════════════════════════
info "Step 2/5 — Creating Service Principal for Terraform & ingestion..."

SP_APP_NAME="${APP_NAME}-sp-${ENVIRONMENT}"
EXISTING_SP=$(az ad app list --display-name "$SP_APP_NAME" --query "[0].appId" -o tsv 2>/dev/null)

if [[ -n "$EXISTING_SP" && "$EXISTING_SP" != "None" ]]; then
  warn "Service Principal app '${SP_APP_NAME}' already exists. Creating new secret only."
  SP_APP_ID="$EXISTING_SP"
  SP_SECRET=$(az ad app credential reset --id "$SP_APP_ID" \
    --display-name "azcops-bootstrap-$(date +%Y%m%d)" \
    --years 1 --query password -o tsv)
else
  # Create dedicated SP app registration
  SP_APP_ID=$(az ad app create \
    --display-name "$SP_APP_NAME" \
    --query appId -o tsv)

  # Create the actual service principal object
  az ad sp create --id "$SP_APP_ID" >/dev/null 2>&1 || true
  sleep 5  # Entra ID propagation delay

  # Generate client secret
  SP_SECRET=$(az ad app credential reset --id "$SP_APP_ID" \
    --display-name "azcops-bootstrap-$(date +%Y%m%d)" \
    --years 1 --query password -o tsv)

  success "Service Principal created: ${SP_APP_ID}"
fi

# Get the SP object ID for role assignments
SP_OBJECT_ID=$(az ad sp show --id "$SP_APP_ID" --query id -o tsv 2>/dev/null) || \
  SP_OBJECT_ID=$(az ad sp list --filter "appId eq '${SP_APP_ID}'" --query "[0].id" -o tsv)

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Role Assignments
# ═══════════════════════════════════════════════════════════════════════════════
info "Step 3/5 — Assigning roles on subscription..."
SCOPE="/subscriptions/${SUBSCRIPTION_ID}"

assign_role() {
  local ROLE="$1"
  local SCOPE="$2"
  if az role assignment list --assignee "$SP_OBJECT_ID" --role "$ROLE" --scope "$SCOPE" \
       --query "[0].id" -o tsv 2>/dev/null | grep -q .; then
    warn "Role '${ROLE}' already assigned. Skipping."
  else
    az role assignment create \
      --assignee-object-id "$SP_OBJECT_ID" \
      --assignee-principal-type ServicePrincipal \
      --role "$ROLE" \
      --scope "$SCOPE" >/dev/null
    success "Assigned: ${ROLE}"
  fi
}

assign_role "Reader"                  "$SCOPE"
assign_role "Cost Management Reader"  "$SCOPE"

# Contributor on a dedicated resource group for Terraform to manage infra
TF_RG_SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${APP_NAME}-${ENVIRONMENT}-rg"
az group create --name "${APP_NAME}-${ENVIRONMENT}-rg" \
  --location "$LOCATION" --tags "project=AzCops" "env=${ENVIRONMENT}" >/dev/null 2>&1 || true
assign_role "Contributor" "$TF_RG_SCOPE"

success "Role assignments complete."

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Terraform State Storage
# ═══════════════════════════════════════════════════════════════════════════════
info "Step 4/5 — Creating Terraform state storage..."

# Create resource group for tfstate
az group create --name "$TF_STATE_RG" --location "$LOCATION" \
  --tags "project=AzCops" "purpose=terraform-state" >/dev/null
success "Resource group: ${TF_STATE_RG}"

# Storage account (check if one already exists in the RG)
EXISTING_SA=$(az storage account list --resource-group "$TF_STATE_RG" \
  --query "[0].name" -o tsv 2>/dev/null)
if [[ -n "$EXISTING_SA" && "$EXISTING_SA" != "None" ]]; then
  warn "Storage account '${EXISTING_SA}' already exists in ${TF_STATE_RG}. Reusing."
  TF_STATE_SA="$EXISTING_SA"
else
  # Ensure globally unique name (lowercase, max 24 chars)
  TF_STATE_SA="azcops${ENVIRONMENT}tf$(echo "$SUBSCRIPTION_ID" | tr -d '-' | cut -c1-10)"
  az storage account create \
    --name "$TF_STATE_SA" \
    --resource-group "$TF_STATE_RG" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --min-tls-version TLS1_2 \
    --allow-blob-public-access false \
    --tags "project=AzCops" "purpose=terraform-state" >/dev/null
  success "Storage account: ${TF_STATE_SA}"
fi

# Container for tfstate
az storage container create \
  --name "$TF_STATE_CONTAINER" \
  --account-name "$TF_STATE_SA" \
  --auth-mode login >/dev/null 2>&1 || \
az storage container create \
  --name "$TF_STATE_CONTAINER" \
  --account-name "$TF_STATE_SA" >/dev/null 2>&1 || true
success "Container: ${TF_STATE_CONTAINER}"

# Grant the SP Storage Blob Data Contributor on tfstate SA
TF_SA_ID=$(az storage account show --name "$TF_STATE_SA" \
  --resource-group "$TF_STATE_RG" --query id -o tsv)
assign_role "Storage Blob Data Contributor" "$TF_SA_ID"

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5 — Write output files
# ═══════════════════════════════════════════════════════════════════════════════
info "Step 5/5 — Writing output files..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ── .env file for backend API ─────────────────────────────────────────────────
ENV_FILE="${REPO_ROOT}/src/api/.env"
cat > "$ENV_FILE" <<ENVEOF
# AzCops API — generated by bootstrap-spn.sh on $(date)
# DO NOT COMMIT THIS FILE

DATABASE_URL=postgresql+asyncpg://azcops:azcops_dev_password@localhost:5432/azcops

# Azure Entra ID (for JWT validation)
AZURE_TENANT_ID=${TENANT_ID}
AZURE_CLIENT_ID=${SP_APP_ID}
AZURE_CLIENT_SECRET=${SP_SECRET}

# Key Vault (set after terraform apply)
AZURE_KEYVAULT_URI=

# Data Lake Storage (set after terraform apply)
AZURE_STORAGE_ACCOUNT_NAME=
AZURE_STORAGE_CONTAINER_NAME=raw

# API settings
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000"]
AUTH_ENABLED=false
AUTH_AUDIENCE=api://${CLIENT_ID}
AUTH_ISSUER=https://login.microsoftonline.com/${TENANT_ID}/v2.0
ENVEOF
success "Written: src/api/.env"

# ── .env.local for Next.js UI ─────────────────────────────────────────────────
ENV_LOCAL="${REPO_ROOT}/src/ui/.env.local"
cat > "$ENV_LOCAL" <<ENVEOF
# AzCops UI — generated by bootstrap-spn.sh on $(date)
# DO NOT COMMIT THIS FILE

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_AZURE_CLIENT_ID=${CLIENT_ID}
NEXT_PUBLIC_AZURE_TENANT_ID=${TENANT_ID}
NEXT_PUBLIC_AZURE_REDIRECT_URI=${REDIRECT_URI}
ENVEOF
success "Written: src/ui/.env.local"

# ── terraform.tfvars for dev environment ──────────────────────────────────────
TFVARS="${REPO_ROOT}/infra/terraform/environments/dev/terraform.tfvars"
cat > "$TFVARS" <<TFEOF
# AzCops Terraform — generated by bootstrap-spn.sh on $(date)
# DO NOT COMMIT THIS FILE

subscription_id   = "${SUBSCRIPTION_ID}"
tenant_id         = "${TENANT_ID}"
environment       = "${ENVIRONMENT}"
location          = "${LOCATION}"
project_name      = "${APP_NAME}"

# Service Principal (for Terraform provider auth)
client_id         = "${SP_APP_ID}"
client_secret     = "${SP_SECRET}"
TFEOF
success "Written: infra/terraform/environments/dev/terraform.tfvars"

# ── backend.tf (uncommented, ready to use) ────────────────────────────────────
BACKEND_TF="${REPO_ROOT}/infra/terraform/environments/dev/backend.tf"
cat > "$BACKEND_TF" <<BACKENDEOF
# AzCops Terraform Remote State — generated by bootstrap-spn.sh
terraform {
  backend "azurerm" {
    resource_group_name  = "${TF_STATE_RG}"
    storage_account_name = "${TF_STATE_SA}"
    container_name       = "${TF_STATE_CONTAINER}"
    key                  = "azcops-${ENVIRONMENT}.tfstate"
    use_azuread_auth     = true
  }
}
BACKENDEOF
success "Written: infra/terraform/environments/dev/backend.tf"

# ── GitHub Actions secrets export ─────────────────────────────────────────────
GH_SECRETS="${SCRIPT_DIR}/github-secrets.env"
cat > "$GH_SECRETS" <<GHEOF
# Run these with: gh secret set <NAME> --body "<VALUE>" --repo gowrishacv/AzCops
# Or paste into: GitHub → Settings → Secrets → Actions

AZURE_TENANT_ID=${TENANT_ID}
AZURE_CLIENT_ID=${SP_APP_ID}
AZURE_CLIENT_SECRET=${SP_SECRET}
AZURE_SUBSCRIPTION_ID=${SUBSCRIPTION_ID}
TF_STATE_RESOURCE_GROUP=${TF_STATE_RG}
TF_STATE_STORAGE_ACCOUNT=${TF_STATE_SA}
TF_STATE_CONTAINER=${TF_STATE_CONTAINER}
GHEOF
success "Written: infra/scripts/github-secrets.env"

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅  Bootstrap complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}App Registration (UI auth)${NC}"
echo -e "    Client ID  : ${CLIENT_ID}"
echo -e "    Tenant ID  : ${TENANT_ID}"
echo ""
echo -e "  ${CYAN}Service Principal (Terraform + ingestion)${NC}"
echo -e "    App ID     : ${SP_APP_ID}"
echo -e "    Object ID  : ${SP_OBJECT_ID}"
echo -e "    Tenant ID  : ${TENANT_ID}"
echo -e "    Secret     : ${SP_SECRET:0:8}…  (full value in .env files)"
echo ""
echo -e "  ${CYAN}Terraform State${NC}"
echo -e "    RG         : ${TF_STATE_RG}"
echo -e "    SA         : ${TF_STATE_SA}"
echo -e "    Container  : ${TF_STATE_CONTAINER}"
echo ""
echo -e "  ${CYAN}Files written (do NOT commit these):${NC}"
echo -e "    src/api/.env"
echo -e "    src/ui/.env.local"
echo -e "    infra/terraform/environments/dev/terraform.tfvars"
echo -e "    infra/terraform/environments/dev/backend.tf"
echo -e "    infra/scripts/github-secrets.env"
echo ""
echo -e "  ${CYAN}Next steps:${NC}"
echo -e "    1.  cd infra/terraform/environments/dev"
echo -e "    2.  terraform init"
echo -e "    3.  terraform plan"
echo -e "    4.  terraform apply"
echo ""
echo -e "  ${CYAN}To set GitHub Actions secrets:${NC}"
echo -e "    cat infra/scripts/github-secrets.env"
echo -e "    gh secret set AZURE_CLIENT_SECRET --body \"${SP_SECRET}\" --repo gowrishacv/AzCops"
echo -e "    (repeat for each variable)"
echo ""
warn "SECURITY: .env files contain secrets. They are in .gitignore and must NOT be committed."
echo ""
