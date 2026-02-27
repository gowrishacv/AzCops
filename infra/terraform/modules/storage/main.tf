###############################################################################
# Storage Module
# Creates Azure Storage Account with Data Lake Gen2 and private endpoint
# CAF: st{workload}{env}{region} — NO hyphens, all lowercase, max 24 chars
#   stazcopsdevweu = 14 chars (within limit)
###############################################################################

# ---------------------------------------------------------------------------
# Storage Account (Data Lake Gen2)
# ---------------------------------------------------------------------------

resource "azurerm_storage_account" "this" {
  name                          = replace("st${var.project}${var.environment}${var.region_short}", "-", "")
  resource_group_name           = var.resource_group_name
  location                      = var.location
  account_tier                  = var.account_tier
  account_replication_type      = var.replication_type
  account_kind                  = "StorageV2"
  is_hns_enabled                = true # Enable Data Lake Gen2
  min_tls_version               = "TLS1_2"
  public_network_access_enabled = false

  blob_properties {
    delete_retention_policy {
      days = var.blob_retention_days
    }

    container_delete_retention_policy {
      days = var.container_retention_days
    }
  }

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Storage Container - Raw API responses
# ---------------------------------------------------------------------------

resource "azurerm_storage_data_lake_gen2_filesystem" "raw" {
  name               = "raw"
  storage_account_id = azurerm_storage_account.this.id
}

# ---------------------------------------------------------------------------
# Private Endpoint for DFS (Data Lake Storage)
# CAF: pep-{resource}-{workload}-{env}
# ---------------------------------------------------------------------------

resource "azurerm_private_endpoint" "dfs" {
  name                = "pep-dfs-${var.project}-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "${var.project}-${var.environment}-dfs-psc"
    private_connection_resource_id = azurerm_storage_account.this.id
    is_manual_connection           = false
    subresource_names              = ["dfs"]
  }

  private_dns_zone_group {
    name                 = "dfs-dns-zone-group"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }
}

# ---------------------------------------------------------------------------
# Role Assignment - Grant managed identity access to storage
# ---------------------------------------------------------------------------
# NOTE: count/for_each conditionals require values known at plan time.
# Since managed_identity_principal_id is a downstream module output
# (unknown until apply), we use a plain resource with no conditional.
# Terraform resolves the dependency graph and applies this after identity.

resource "azurerm_role_assignment" "storage_blob_data_contributor" {
  scope                = azurerm_storage_account.this.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.managed_identity_principal_id
}
