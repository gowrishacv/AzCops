###############################################################################
# Key Vault Module - Outputs
###############################################################################

output "id" {
  description = "The ID of the Key Vault"
  value       = azurerm_key_vault.this.id
}

output "name" {
  description = "The name of the Key Vault"
  value       = azurerm_key_vault.this.name
}

output "vault_uri" {
  description = "The URI of the Key Vault"
  value       = azurerm_key_vault.this.vault_uri
}

output "private_endpoint_id" {
  description = "The ID of the Key Vault private endpoint"
  value       = azurerm_private_endpoint.keyvault.id
}
