#!/usr/bin/env python
import requests  # To perform the API queries
import json  # To format and display the final output
import urllib3  # To disable SSL warning below
import pynautobot
from pprint import pprint
import ipaddress


# disable SSL warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# User definable variables
netbox_url = "https://192.168.14.138"
netbox_token = "1626435c136f5b1ed4983ad171a4b01e1d55ba73"

# API call parameters.  The second line is needed if nautobot is using self-signed SSL certificates
nb = pynautobot.api(url=netbox_url, token=netbox_token)
nb.http_session.verify = False

# Function to take in a query and return the output in json
def gqlAPI(query):
    return nb.graphql.query(query=query).json

# GraphQL Query that returns config contexts and the enclave or device roles they are tied to
enclaveRoleQuery = """
{
  config_contexts {
    name
    data
    roles {
      devices {
        name
      }
    }
    platforms {
      devices {
        name
      }
    }
  }
}
"""
# GraphQL Query that returns list of tenants and their assigned subnets
tenantQuery = """
{
  tenants {
    name
    devices {
      name
    }
    networks:prefixes {
      role {
        name
      }
			is_pool
      prefix
    }
  }
}
"""
# GraphQL Query to return list of all devices and their serial numbers and primary ipv4 address
hostQuery = """
{
  _meta: devices {
    name
    serial
    primary_ip4 {
      host
    }
  }
}
"""

# Run the GraphQL API calls using the queries above
enclavesRoles = gqlAPI(enclaveRoleQuery)
tenants = gqlAPI(tenantQuery)
hosts = gqlAPI(hostQuery)

# Separate and briefly format the data returned in the above API calls
enclaveGroups = [group for group in enclavesRoles["data"]["config_contexts"] if group["platforms"]]
roleGroups = [group for group in enclavesRoles["data"]["config_contexts"] if group["roles"]]
tenantGroups = tenants["data"]["tenants"]
hosts = hosts["data"]["_meta"]

"""
The code below restructures the json output from the above queries.
Groups are created and variables are assigned to each group.
This code uses both dictionary and list comprehensions which can be complicated,
but the code is formatted to give you an idea of what the resultant dictionaries will look like.
"""

# Create groups for each enclave
finalEnclaveGroups = {
    group["name"]: {
        "hosts": [device["name"] for device in group["platforms"][0]["devices"]],
        "vars": group["data"],
    }
    for group in enclaveGroups
}

# Create groups for each device role
finalRoleGroups = {
    group["name"]: {
        "hosts": [device["name"] for role in group["roles"] for device in role["devices"]],
        "vars": group["data"],
    }
    for group in roleGroups
}

# Create a group for each tenant
finalTenantGroups = {
    tenant["name"]: {
        "hosts": [device["name"] for device in tenant["devices"]],
        "vars": {
            "networks": {
                network["role"]["name"]: {
                    "is_pool": network["is_pool"],
                    "network": network["prefix"],
                    "last_usable": str(ipaddress.ip_network(network["prefix"])[-2]),
                    "first_usable": str(ipaddress.ip_network(network["prefix"])[1]),
                }
                for network in tenant["networks"]
            }
        },
    }
    for tenant in tenantGroups
}

# Create a final host dictionary with the key '_meta'.  Only variables included are serial number and ansible_host
finalHosts = {
    "_meta": {
        "hostvars": {
            host.pop("name"): {
                "ansible_host": host["primary_ip4"]["host"] if host["primary_ip4"] else "",
                "device_serial": host["serial"] if host["serial"] else "",
            }
            for host in hosts
        }
    }
}

# Some pretty print calls that you can uncomment for debugging
# pprint(finalEnclaveGroups)
# pprint(finalRoleGroups)
# pprint(finalTenantGroups)
# pprint(finalHosts)

# Create an empty dictionary that will be the result.  Then append each of the above dictionaries one by one.
inventory = {}
inventory.update(finalEnclaveGroups)
inventory.update(finalRoleGroups)
inventory.update(finalTenantGroups)
inventory.update(finalHosts)

print(json.dumps(inventory, indent=4, sort_keys=True))
