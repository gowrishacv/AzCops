###############################################################################
# AzCops - Dev Environment
# Orchestrates all modules for the development environment
# Naming follows Microsoft Cloud Adoption Framework (CAF):
# https://learn.microsoft.com/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming
###############################################################################

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0, < 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }
  subscription_id = var.subscription_id
}

# ---------------------------------------------------------------------------
# Locals
# ---------------------------------------------------------------------------

locals {
  # Normalise to lowercase so CAF names are always valid regardless of
  # the casing used in the tfvars file.
  project     = lower(var.project_name)
  environment = lower(var.environment)

  # CAF region abbreviation lookup
  # https://learn.microsoft.com/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming
  region_short = lookup({
    "westeurope"    = "weu"
    "northeurope"   = "neu"
    "eastus"        = "eus"
    "eastus2"       = "eus2"
    "westus2"       = "wus2"
    "uksouth"       = "uks"
    "ukwest"        = "ukw"
    "australiaeast" = "aue"
    "southeastasia" = "sea"
  }, var.location, replace(var.location, " ", ""))

  # CAF name suffix shared by all modules: {workload}-{env}-{region}
  name_suffix = "${local.project}-${local.environment}-${local.region_short}"

  common_tags = merge(var.tags, {
    project     = local.project
    environment = local.environment
    managed_by  = "terraform"
  })
}

# ---------------------------------------------------------------------------
# Generate a random password for PostgreSQL admin
# ---------------------------------------------------------------------------

resource "random_password" "postgresql" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# ---------------------------------------------------------------------------
# Resource Group
# ---------------------------------------------------------------------------

module "resource_group" {
  source = "../../modules/resource_group"

  # CAF: rg-{workload}-{env}-{region}
  name     = "rg-${local.name_suffix}"
  location = var.location
  tags     = local.common_tags
}

# ---------------------------------------------------------------------------
# Identity (Managed Identity + Role Assignments)
# ---------------------------------------------------------------------------

module "identity" {
  source = "../../modules/identity"

  project             = local.project
  environment         = local.environment
  location            = var.location
  resource_group_name = module.resource_group.name
  subscription_id     = var.subscription_id
  region_short        = local.region_short
  tags                = local.common_tags
}

# ---------------------------------------------------------------------------
# Networking (VNet, Subnets, NSGs, DNS Zones)
# ---------------------------------------------------------------------------

module "networking" {
  source = "../../modules/networking"

  project             = local.project
  environment         = local.environment
  location            = var.location
  resource_group_name = module.resource_group.name
  region_short        = local.region_short
  vnet_address_space  = "10.0.0.0/16"
  subnet_prefixes = {
    api     = "10.0.1.0/24"
    db      = "10.0.2.0/24"
    storage = "10.0.3.0/24"
    app     = "10.0.4.0/24"
  }
  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# PostgreSQL Flexible Server
# ---------------------------------------------------------------------------

module "postgresql" {
  source = "../../modules/postgresql"

  project                      = local.project
  environment                  = local.environment
  location                     = var.location
  resource_group_name          = module.resource_group.name
  region_short                 = local.region_short
  delegated_subnet_id          = module.networking.db_subnet_id
  private_dns_zone_id          = module.networking.postgresql_dns_zone_id
  administrator_login          = "psqladmin"
  administrator_password       = random_password.postgresql.result
  sku_name                     = "B_Standard_B1ms" # Dev-appropriate sizing
  storage_mb                   = 32768             # 32 GB
  backup_retention_days        = 7
  geo_redundant_backup_enabled = false
  tags                         = local.common_tags

  depends_on = [module.networking]
}

# ---------------------------------------------------------------------------
# Key Vault
# ---------------------------------------------------------------------------

module "keyvault" {
  source = "../../modules/keyvault"

  project                    = local.project
  environment                = local.environment
  location                   = var.location
  resource_group_name        = module.resource_group.name
  region_short               = local.region_short
  subnet_id                  = module.networking.api_subnet_id
  private_dns_zone_id        = module.networking.keyvault_dns_zone_id
  managed_identity_object_id = module.identity.principal_id
  soft_delete_retention_days = 90
  purge_protection_enabled   = false        # false in dev — allows easy teardown
  enable_public_access       = true         # true in dev — Terraform runs locally outside the VNet
                                            # set false in prod (use private CI runner inside VNet)
  tags                       = local.common_tags

  depends_on = [module.networking, module.identity]
}

# ---------------------------------------------------------------------------
# Storage Account (Data Lake Gen2)
# ---------------------------------------------------------------------------

module "storage" {
  source = "../../modules/storage"

  project                       = local.project
  environment                   = local.environment
  location                      = var.location
  resource_group_name           = module.resource_group.name
  region_short                  = local.region_short
  subnet_id                     = module.networking.storage_subnet_id
  private_dns_zone_id           = module.networking.dfs_dns_zone_id
  managed_identity_principal_id = module.identity.principal_id
  account_tier                  = "Standard"
  replication_type              = "LRS"   # Dev uses locally redundant storage
  enable_public_access          = true    # true in dev — Terraform runs locally outside the VNet
                                          # set false in prod (use private CI runner inside VNet)
  tags                          = local.common_tags

  depends_on = [module.networking, module.identity]
}

# ---------------------------------------------------------------------------
# Store PostgreSQL password in Key Vault
# ---------------------------------------------------------------------------

resource "azurerm_key_vault_secret" "postgresql_password" {
  name         = "postgresql-admin-password"
  value        = random_password.postgresql.result
  key_vault_id = module.keyvault.id
  tags         = local.common_tags

  depends_on = [module.keyvault]
}

resource "azurerm_key_vault_secret" "postgresql_connection_string" {
  name         = "postgresql-connection-string"
  value        = module.postgresql.connection_string
  key_vault_id = module.keyvault.id
  tags         = local.common_tags

  depends_on = [module.keyvault, module.postgresql]
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "resource_group_name" {
  description = "The name of the resource group"
  value       = module.resource_group.name
}

output "resource_group_id" {
  description = "The ID of the resource group"
  value       = module.resource_group.id
}

output "vnet_id" {
  description = "The ID of the virtual network"
  value       = module.networking.vnet_id
}

output "postgresql_server_fqdn" {
  description = "The FQDN of the PostgreSQL server"
  value       = module.postgresql.server_fqdn
}

output "postgresql_database_name" {
  description = "The name of the PostgreSQL database"
  value       = module.postgresql.database_name
}

output "keyvault_uri" {
  description = "The URI of the Key Vault"
  value       = module.keyvault.vault_uri
}

output "storage_account_name" {
  description = "The name of the storage account"
  value       = module.storage.name
}

output "storage_dfs_endpoint" {
  description = "The primary DFS endpoint"
  value       = module.storage.primary_dfs_endpoint
}

output "managed_identity_client_id" {
  description = "The client ID of the managed identity"
  value       = module.identity.client_id
}

output "managed_identity_principal_id" {
  description = "The principal ID of the managed identity"
  value       = module.identity.principal_id
}
