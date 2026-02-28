# GitHub Actions OIDC — Workload Identity Federation

## Why OIDC?

GitHub Actions can authenticate to Azure **without storing a long-lived client secret** as a GitHub secret. Instead, GitHub issues a short-lived OIDC token per workflow run, and Azure trusts that token via a Federated Identity Credential.

**Benefits:**
- No client secrets to rotate
- Tokens expire in minutes
- Fine-grained trust: only specific repo / branch / environment can obtain tokens

---

## One-time Setup

### 1. Create the Federated Identity Credential

```bash
# Replace with your values
GITHUB_ORG="your-org-or-username"
GITHUB_REPO="AzCops"
APP_ID="<your-app-registration-object-id>"

# Allow 'main' branch to authenticate
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "azcops-github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$GITHUB_ORG/$GITHUB_REPO"':ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Allow the 'dev' GitHub Environment (for terraform-apply.yml)
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "azcops-github-env-dev",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$GITHUB_ORG/$GITHUB_REPO"':environment:dev",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Allow PRs to run terraform plan
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "azcops-github-pr",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$GITHUB_ORG/$GITHUB_REPO"':pull_request",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### 2. Set GitHub Secrets

```bash
gh secret set AZURE_CLIENT_ID      --body "<app-registration-client-id>"
gh secret set AZURE_TENANT_ID      --body "<your-tenant-id>"
gh secret set AZURE_SUBSCRIPTION_ID --body "<your-subscription-id>"
# Keep CLIENT_SECRET for non-OIDC fallback (e.g., local dev)
gh secret set AZURE_CLIENT_SECRET  --body "<client-secret>"
```

### 3. Configure GitHub Environment

1. Go to **Settings → Environments → New environment** → name it `dev`
2. Add **Required reviewers** (yourself or a team)
3. This gates `terraform-apply.yml` — it won't run until a reviewer approves

---

## How It Works in the Workflow

```yaml
- name: Azure login (OIDC)
  uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
    # No client-secret → uses OIDC automatically
```

The `id-token: write` permission in the workflow grants GitHub the ability to issue an OIDC token for the run.

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `AADSTS70021: No matching federated identity record found` | Subject mismatch (branch vs env vs PR) | Create the correct federated credential for the trigger type |
| `AADSTS700016: Application not found` | Wrong client ID | Check `AZURE_CLIENT_ID` secret matches the App Registration |
| `AuthorizationFailed` on Terraform resources | SP missing role | Assign `Contributor` or scoped role to the SP |
