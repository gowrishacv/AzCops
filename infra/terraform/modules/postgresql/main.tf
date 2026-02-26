###############################################################################
# PostgreSQL Flexible Server Module
# Creates Azure Database for PostgreSQL Flexible Server with private networking
###############################################################################

# ---------------------------------------------------------------------------
# PostgreSQL Flexible Server
# ---------------------------------------------------------------------------

resource "azurerm_postgresql_flexible_server" "this" {
  name                          = "${var.project}-${var.environment}-psql"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  version                       = "16"
  delegated_subnet_id           = var.delegated_subnet_id
  private_dns_zone_id           = var.private_dns_zone_id
  administrator_login           = var.administrator_login
  administrator_password        = var.administrator_password
  sku_name                      = var.sku_name
  storage_mb                    = var.storage_mb
  backup_retention_days         = var.backup_retention_days
  geo_redundant_backup_enabled  = var.geo_redundant_backup_enabled
  public_network_access_enabled = false
  zone                          = var.availability_zone

  tags = var.tags

  lifecycle {
    ignore_changes = [
      # Prevent Terraform from trying to update the password on every apply
      administrator_password,
    ]
  }
}

# ---------------------------------------------------------------------------
# PostgreSQL Configuration - Enforce SSL
# ---------------------------------------------------------------------------

resource "azurerm_postgresql_flexible_server_configuration" "require_secure_transport" {
  name      = "require_secure_transport"
  server_id = azurerm_postgresql_flexible_server.this.id
  value     = "on"
}

resource "azurerm_postgresql_flexible_server_configuration" "ssl_min_protocol_version" {
  name      = "ssl_min_protocol_version"
  server_id = azurerm_postgresql_flexible_server.this.id
  value     = "TLSv1.2"
}

# ---------------------------------------------------------------------------
# PostgreSQL Database
# ---------------------------------------------------------------------------

resource "azurerm_postgresql_flexible_server_database" "azcops" {
  name      = "${var.project}_${var.environment}"
  server_id = azurerm_postgresql_flexible_server.this.id
  collation = "en_US.utf8"
  charset   = "UTF8"
}
