###############################################################################
# Key Vault Module - Variables
###############################################################################

variable "project" {
  description = "Project name used for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "location" {
  description = "Azure region for the Key Vault"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group to deploy into"
  type        = string
}

variable "subnet_id" {
  description = "The ID of the subnet for the Key Vault private endpoint"
  type        = string
}

variable "private_dns_zone_id" {
  description = "The ID of the private DNS zone for Key Vault"
  type        = string
}

variable "managed_identity_object_id" {
  description = "The object ID of the managed identity to grant access to the Key Vault"
  type        = string
  default     = ""
}

variable "soft_delete_retention_days" {
  description = "Number of days to retain soft-deleted items"
  type        = number
  default     = 90
}

variable "purge_protection_enabled" {
  description = "Whether purge protection is enabled for the Key Vault"
  type        = bool
  default     = true
}

variable "region_short" {
  description = "Short region code for CAF resource naming (e.g. weu, eus2)"
  type        = string
}

variable "enable_public_access" {
  description = <<-EOT
    Allow public network access to the Key Vault.
    Set true for dev (Terraform runs from local machine outside the VNet).
    Set false for prod (Terraform runs from a private CI runner inside the VNet).
  EOT
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to all Key Vault resources"
  type        = map(string)
  default     = {}
}
