"""
KQL query templates for Azure Resource Graph.
All queries are parameterised — no subscription IDs are hardcoded.
"""

# Full inventory — every resource in scope
ALL_RESOURCES = """
Resources
| project
    id,
    name,
    type,
    resourceGroup,
    subscriptionId,
    location,
    tags,
    properties,
    kind
| order by type asc
"""

# Unattached managed disks
UNATTACHED_DISKS = """
Resources
| where type =~ 'microsoft.compute/disks'
| extend diskState = tostring(properties.diskState)
| where diskState =~ 'Unattached'
| extend sizeGB = toint(properties.diskSizeGB)
| extend skuName = tostring(sku.name)
| project id, name, resourceGroup, subscriptionId, location, sizeGB, skuName, tags
"""

# Idle public IP addresses (not associated with any resource)
ORPHANED_PUBLIC_IPS = """
Resources
| where type =~ 'microsoft.network/publicipaddresses'
| where isnull(properties.ipConfiguration) and isnull(properties.natGateway)
| extend skuName = tostring(sku.name)
| project id, name, resourceGroup, subscriptionId, location, skuName, tags
"""

# Orphaned network interface cards (not attached to a VM)
ORPHANED_NICS = """
Resources
| where type =~ 'microsoft.network/networkinterfaces'
| where isnull(properties.virtualMachine)
| project id, name, resourceGroup, subscriptionId, location, tags
"""

# Stale snapshots older than 90 days
STALE_SNAPSHOTS = """
Resources
| where type =~ 'microsoft.compute/snapshots'
| extend timeCreated = todatetime(properties.timeCreated)
| where timeCreated < ago(90d)
| extend sizeGB = toint(properties.diskSizeGB)
| project id, name, resourceGroup, subscriptionId, location, sizeGB, timeCreated, tags
"""

# All VMs — used by right-sizing rules (enriched with Monitor metrics separately)
ALL_VMS = """
Resources
| where type =~ 'microsoft.compute/virtualmachines'
| extend vmSize = tostring(properties.hardwareProfile.vmSize)
| extend osType = tostring(properties.storageProfile.osDisk.osType)
| extend powerState = tostring(properties.extended.instanceView.powerState.displayStatus)
| project id, name, resourceGroup, subscriptionId, location, vmSize, osType, powerState, tags
"""

# App Service Plans — used for right-sizing
APP_SERVICE_PLANS = """
Resources
| where type =~ 'microsoft.web/serverfarms'
| extend skuName = tostring(sku.name)
| extend skuTier = tostring(sku.tier)
| extend currentWorkers = toint(properties.numberOfWorkers)
| extend maximumElasticWorkerCount = toint(properties.maximumElasticWorkerCount)
| project id, name, resourceGroup, subscriptionId, location, skuName, skuTier, currentWorkers, tags
"""

# SQL Servers and databases
SQL_DATABASES = """
Resources
| where type =~ 'microsoft.sql/servers/databases'
| extend skuName = tostring(sku.name)
| extend skuTier = tostring(sku.tier)
| extend skuCapacity = toint(sku.capacity)
| where name !~ 'master'
| project id, name, resourceGroup, subscriptionId, location, skuName, skuTier, skuCapacity, tags
"""

# Resources missing the 'cost-center' tag (governance rule)
MISSING_COST_CENTER_TAG = """
Resources
| where isnull(tags['cost-center']) or tags['cost-center'] =~ ''
| where type !in~ (
    'microsoft.resources/subscriptions/resourcegroups',
    'microsoft.authorization/roleassignments'
  )
| project id, name, type, resourceGroup, subscriptionId, location, tags
| order by type asc
"""
