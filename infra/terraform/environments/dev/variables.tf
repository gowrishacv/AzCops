###############################################################################
# AzCops Dev Environment - Variables
###############################################################################

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus2"
}

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "tags" {
  description = "Additional tags to apply to all resources (merged with default tags)"
  type        = map(string)
  default     = {}
}
