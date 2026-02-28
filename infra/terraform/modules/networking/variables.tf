###############################################################################
# Networking Module - Variables
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
  description = "Azure region for network resources"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group to deploy into"
  type        = string
}

variable "vnet_address_space" {
  description = "Address space for the virtual network"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_prefixes" {
  description = "Map of subnet name to address prefix"
  type        = map(string)
  default = {
    api     = "10.0.1.0/24"
    db      = "10.0.2.0/24"
    storage = "10.0.3.0/24"
    app     = "10.0.4.0/24"
  }
}

variable "region_short" {
  description = "Short region code for CAF resource naming (e.g. weu, eus2)"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all networking resources"
  type        = map(string)
  default     = {}
}
