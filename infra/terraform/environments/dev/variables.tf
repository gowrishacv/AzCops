###############################################################################
# AzCops Dev Environment — Variables
# Naming follows Microsoft Cloud Adoption Framework (CAF):
# https://learn.microsoft.com/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming
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
  description = "Project / workload name — used in every CAF resource name"
  type        = string
  default     = "azcops"
}

variable "client_id" {
  description = "Service principal client ID for the Terraform azurerm provider"
  type        = string
}

variable "client_secret" {
  description = "Service principal client secret for the Terraform azurerm provider"
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Additional tags merged with default tags on every resource"
  type        = map(string)
  default     = {}
}
