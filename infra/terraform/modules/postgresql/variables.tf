###############################################################################
# PostgreSQL Module - Variables
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
  description = "Azure region for the PostgreSQL server"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group to deploy into"
  type        = string
}

variable "delegated_subnet_id" {
  description = "The ID of the subnet delegated to PostgreSQL Flexible Server"
  type        = string
}

variable "private_dns_zone_id" {
  description = "The ID of the private DNS zone for PostgreSQL"
  type        = string
}

variable "administrator_login" {
  description = "Administrator login name for the PostgreSQL server"
  type        = string
  default     = "psqladmin"
}

variable "administrator_password" {
  description = "Administrator password for the PostgreSQL server"
  type        = string
  sensitive   = true
}

variable "sku_name" {
  description = "SKU name for the PostgreSQL server (e.g., B_Standard_B1ms for dev, GP_Standard_D2s_v3 for prod)"
  type        = string
  default     = "B_Standard_B1ms"
}

variable "storage_mb" {
  description = "Storage size in MB for the PostgreSQL server"
  type        = number
  default     = 32768 # 32 GB
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

variable "geo_redundant_backup_enabled" {
  description = "Whether geo-redundant backups are enabled"
  type        = bool
  default     = false
}

variable "availability_zone" {
  description = "Availability zone for the PostgreSQL server"
  type        = string
  default     = "1"
}

variable "tags" {
  description = "Tags to apply to all PostgreSQL resources"
  type        = map(string)
  default     = {}
}
