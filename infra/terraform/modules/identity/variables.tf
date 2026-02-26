###############################################################################
# Identity Module - Variables
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
  description = "Azure region for the managed identity"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group to deploy into"
  type        = string
}

variable "subscription_id" {
  description = "The Azure subscription ID for role assignments"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all identity resources"
  type        = map(string)
  default     = {}
}
