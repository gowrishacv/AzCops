###############################################################################
# Identity Module
# Creates User-Assigned Managed Identity with Azure role assignments
###############################################################################

# ---------------------------------------------------------------------------
# User-Assigned Managed Identity
# CAF: id-{workload}-{env}-{region}
# ---------------------------------------------------------------------------

resource "azurerm_user_assigned_identity" "this" {
  name                = "id-${var.project}-${var.environment}-${var.region_short}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

# ---------------------------------------------------------------------------
# Role Assignments at Subscription Scope
# ---------------------------------------------------------------------------

# Reader role - allows reading all Azure resources (also covers Resource Graph)
resource "azurerm_role_assignment" "reader" {
  scope                = "/subscriptions/${var.subscription_id}"
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}

# Cost Management Reader - allows reading cost and usage data
resource "azurerm_role_assignment" "cost_management_reader" {
  scope                = "/subscriptions/${var.subscription_id}"
  role_definition_name = "Cost Management Reader"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}
