###############################################################################
# AzCops Dev Environment - Variables
###############################################################################

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "westeurope"
}

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "tenant_id" {
  description = "Azure Entra ID tenant ID"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "azcops"
}

variable "client_id" {
  description = "Service principal client ID used by Terraform provider"
  type        = string
}

variable "client_secret" {
  description = "Service principal client secret used by Terraform provider"
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Additional tags to apply to all resources (merged with default tags)"
  type        = map(string)
  default     = {}
}
