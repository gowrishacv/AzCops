###############################################################################
# Storage Module - Variables
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
  description = "Azure region for the storage account"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group to deploy into"
  type        = string
}

variable "subnet_id" {
  description = "The ID of the subnet for the storage private endpoint"
  type        = string
}

variable "private_dns_zone_id" {
  description = "The ID of the private DNS zone for DFS"
  type        = string
}

variable "managed_identity_principal_id" {
  description = "The principal ID of the managed identity to grant storage access"
  type        = string
  default     = ""
}

variable "account_tier" {
  description = "The tier of the storage account (Standard or Premium)"
  type        = string
  default     = "Standard"
}

variable "replication_type" {
  description = "The replication type for the storage account (LRS, GRS, RAGRS, ZRS)"
  type        = string
  default     = "LRS"
}

variable "blob_retention_days" {
  description = "Number of days to retain deleted blobs"
  type        = number
  default     = 7
}

variable "container_retention_days" {
  description = "Number of days to retain deleted containers"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Tags to apply to all storage resources"
  type        = map(string)
  default     = {}
}
