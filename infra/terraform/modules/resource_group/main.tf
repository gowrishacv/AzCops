###############################################################################
# Resource Group Module
# Creates an Azure Resource Group with consistent tagging
###############################################################################

resource "azurerm_resource_group" "this" {
  name     = var.name
  location = var.location
  tags     = var.tags
}
