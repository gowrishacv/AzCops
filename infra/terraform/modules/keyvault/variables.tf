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

variable "tags" {
  description = "Tags to apply to all Key Vault resources"
  type        = map(string)
  default     = {}
}
