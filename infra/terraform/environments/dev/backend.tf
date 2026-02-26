###############################################################################
# Terraform Backend Configuration
#
# INITIAL SETUP:
# Before enabling the remote backend, you must first create the storage account
# and container for state management. Run the following Azure CLI commands:
#
#   az group create \
#     --name azcops-tfstate-rg \
#     --location eastus2
#
#   az storage account create \
#     --name azcopsdevtfstate \
#     --resource-group azcops-tfstate-rg \
#     --location eastus2 \
#     --sku Standard_LRS \
#     --encryption-services blob
#
#   az storage container create \
#     --name tfstate \
#     --account-name azcopsdevtfstate
#
# After creating these resources, uncomment the backend block below and run:
#   terraform init -migrate-state
#
# This will migrate your local state to the remote Azure Storage backend.
###############################################################################

# terraform {
#   backend "azurerm" {
#     resource_group_name  = "azcops-tfstate-rg"
#     storage_account_name = "azcopsdevtfstate"
#     container_name       = "tfstate"
#     key                  = "azcops-dev.tfstate"
#   }
# }
