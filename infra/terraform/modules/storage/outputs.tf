###############################################################################
# Storage Module - Outputs
###############################################################################

output "id" {
  description = "The ID of the storage account"
  value       = azurerm_storage_account.this.id
}

output "name" {
  description = "The name of the storage account"
  value       = azurerm_storage_account.this.name
}

output "primary_dfs_endpoint" {
  description = "The primary DFS endpoint of the storage account"
  value       = azurerm_storage_account.this.primary_dfs_endpoint
}

output "primary_blob_endpoint" {
  description = "The primary blob endpoint of the storage account"
  value       = azurerm_storage_account.this.primary_blob_endpoint
}

output "primary_access_key" {
  description = "The primary access key of the storage account"
  value       = azurerm_storage_account.this.primary_access_key
  sensitive   = true
}

output "raw_filesystem_name" {
  description = "The name of the raw Data Lake Gen2 filesystem"
  value       = azurerm_storage_data_lake_gen2_filesystem.raw.name
}

output "private_endpoint_id" {
  description = "The ID of the DFS private endpoint"
  value       = azurerm_private_endpoint.dfs.id
}
