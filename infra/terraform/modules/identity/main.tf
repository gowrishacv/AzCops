###############################################################################
# Identity Module
# Creates User-Assigned Managed Identity with Azure role assignments
###############################################################################

# ---------------------------------------------------------------------------
# User-Assigned Managed Identity
# ---------------------------------------------------------------------------

resource "azurerm_user_assigned_identity" "this" {
  name                = "${var.project}-${var.environment}-identity"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

# ---------------------------------------------------------------------------
# Role Assignments at Subscription Scope
# ---------------------------------------------------------------------------

# Reader role - allows reading all Azure resources
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

# Resource Graph Reader - allows querying Azure Resource Graph
resource "azurerm_role_assignment" "resource_graph_reader" {
  scope                = "/subscriptions/${var.subscription_id}"
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.this.principal_id

  # This is scoped specifically for Resource Graph queries; the Reader role
  # at subscription level is sufficient for Resource Graph access. If a
  # dedicated custom role is needed, replace with a custom role definition.
}
