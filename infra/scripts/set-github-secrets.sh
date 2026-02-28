#!/usr/bin/env bash
# =============================================================================
# AzCops — Upload secrets to GitHub Actions
#
# PREREQUISITES:
#   brew install gh        # GitHub CLI
#   gh auth login          # sign in to GitHub
#   ./infra/scripts/bootstrap-spn.sh   # must run first
#
# USAGE:
#   chmod +x infra/scripts/set-github-secrets.sh
#   ./infra/scripts/set-github-secrets.sh
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_FILE="${SCRIPT_DIR}/github-secrets.env"
REPO="${GITHUB_REPO:-gowrishacv/AzCops}"

command -v gh >/dev/null 2>&1 || error "GitHub CLI not installed. Run: brew install gh && gh auth login"
[[ -f "$SECRETS_FILE" ]] || error "Secrets file not found: ${SECRETS_FILE}\nRun bootstrap-spn.sh first."

info "Setting GitHub Actions secrets for repo: ${REPO}"
echo ""

# Read each KEY=VALUE line (skip comments and blank lines)
while IFS='=' read -r KEY VALUE; do
  [[ -z "$KEY" || "$KEY" =~ ^# ]] && continue
  # Strip inline comments
  VALUE="${VALUE%%#*}"
  # Strip surrounding whitespace
  VALUE="${VALUE#"${VALUE%%[![:space:]]*}"}"
  VALUE="${VALUE%"${VALUE##*[![:space:]]}"}"
  [[ -z "$VALUE" ]] && continue

  gh secret set "$KEY" --body "$VALUE" --repo "$REPO" 2>/dev/null \
    && success "Set: ${KEY}" \
    || echo -e "${RED}[FAIL]${NC}  Could not set: ${KEY} (check gh auth and repo name)"
done < "$SECRETS_FILE"

echo ""
success "All secrets uploaded to github.com/${REPO}/settings/secrets/actions"
echo ""
info "Verify at: https://github.com/${REPO}/settings/secrets/actions"
