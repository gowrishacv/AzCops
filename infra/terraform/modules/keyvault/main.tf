###############################################################################
# Key Vault Module
# Creates Azure Key Vault with private endpoint and managed identity access
# CAF: kv-{workload}-{env}-{region}  (max 24 chars, alphanumeric + hyphens)
###############################################################################

data "azurerm_client_config" "current" {}

# ---------------------------------------------------------------------------
# Key Vault
# kv-azcops-dev-weu = 17 chars (within 3-24 char limit)
# ---------------------------------------------------------------------------

resource "azurerm_key_vault" "this" {
  name                          = "kv-${var.project}-${var.environment}-${var.region_short}"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  sku_name                      = "standard"
  soft_delete_retention_days    = var.soft_delete_retention_days
  purge_protection_enabled      = var.purge_protection_enabled
  # true  → dev:  Terraform writes secrets from the local machine (outside VNet)
  # false → prod: Terraform runs from a private CI runner inside the VNet
  public_network_access_enabled = var.enable_public_access

  # Allow the deploying identity to manage the vault
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    key_permissions = [
      "Get", "List", "Create", "Delete", "Update",
    ]

    secret_permissions = [
      "Get", "List", "Set", "Delete",
    ]

    certificate_permissions = [
      "Get", "List", "Create", "Delete", "Update",
    ]
  }

  # Access policy for the managed identity
  dynamic "access_policy" {
    for_each = var.managed_identity_object_id != "" ? [1] : []
    content {
      tenant_id = data.azurerm_client_config.current.tenant_id
      object_id = var.managed_identity_object_id

      secret_permissions = [
        "Get", "List",
      ]

      key_permissions = [
        "Get", "List",
      ]

      certificate_permissions = [
        "Get", "List",
      ]
    }
  }

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Private Endpoint
# CAF: pep-{resource}-{workload}-{env}
# ---------------------------------------------------------------------------

resource "azurerm_private_endpoint" "keyvault" {
  name                = "pep-kv-${var.project}-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "${var.project}-${var.environment}-kv-psc"
    private_connection_resource_id = azurerm_key_vault.this.id
    is_manual_connection           = false
    subresource_names              = ["vault"]
  }

  private_dns_zone_group {
    name                 = "keyvault-dns-zone-group"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }
}
