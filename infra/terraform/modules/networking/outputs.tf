###############################################################################
# Networking Module - Outputs
###############################################################################

# VNet
output "vnet_id" {
  description = "The ID of the virtual network"
  value       = azurerm_virtual_network.this.id
}

output "vnet_name" {
  description = "The name of the virtual network"
  value       = azurerm_virtual_network.this.name
}

# Subnets
output "api_subnet_id" {
  description = "The ID of the API subnet"
  value       = azurerm_subnet.api.id
}

output "db_subnet_id" {
  description = "The ID of the database subnet"
  value       = azurerm_subnet.db.id
}

output "storage_subnet_id" {
  description = "The ID of the storage subnet"
  value       = azurerm_subnet.storage.id
}

output "app_subnet_id" {
  description = "The ID of the app subnet"
  value       = azurerm_subnet.app.id
}

# Private DNS Zones
output "postgresql_dns_zone_id" {
  description = "The ID of the PostgreSQL private DNS zone"
  value       = azurerm_private_dns_zone.postgresql.id
}

output "postgresql_dns_zone_name" {
  description = "The name of the PostgreSQL private DNS zone"
  value       = azurerm_private_dns_zone.postgresql.name
}

output "keyvault_dns_zone_id" {
  description = "The ID of the Key Vault private DNS zone"
  value       = azurerm_private_dns_zone.keyvault.id
}

output "keyvault_dns_zone_name" {
  description = "The name of the Key Vault private DNS zone"
  value       = azurerm_private_dns_zone.keyvault.name
}

output "dfs_dns_zone_id" {
  description = "The ID of the DFS private DNS zone"
  value       = azurerm_private_dns_zone.dfs.id
}

output "dfs_dns_zone_name" {
  description = "The name of the DFS private DNS zone"
  value       = azurerm_private_dns_zone.dfs.name
}
