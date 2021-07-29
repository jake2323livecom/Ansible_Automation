#!/usr/bin/env python
import requests  # To perform the API queries
import json  # To format and display the final output
import urllib3  # To disable SSL warning below
import pynautobot
from pprint import pprint


# disable SSL warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# User definable variables
netbox_url = "https://192.168.14.138"
netbox_token = "1626435c136f5b1ed4983ad171a4b01e1d55ba73"

# API call parameters
nb = pynautobot.api(url=netbox_url, token=netbox_token)
nb.http_session.verify = False


def gqlAPI(query):
    return nb.graphql.query(query=query).json

enclaveQuery = """
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
hostQuery = """
{
  _meta: devices {
    name
    serial
    primary_ip4 {
      address
    }
  }
}
"""


enclaves = gqlAPI(enclaveQuery)
tenants = gqlAPI(tenantQuery)
hosts = gqlAPI(hostQuery)


enclaveGroups = [ group for group in enclaves["data"]["config_contexts"] if group['platforms']]
roleGroups = [ group for group in enclaves["data"]["config_contexts"] if group['roles'] or group['device_types']]
tenantGroups = tenants["data"]["tenants"]
hosts = hosts["data"]["_meta"]

finalEnclaveGroups = {
    group["name"]: {
        "hosts": [device["name"] for device in group["platforms"][0]["devices"] ],
        "vars": group["data"],
    }
    for group in enclaveGroups
}

finalRoleGroups = {
    group["name"]: {
        "hosts": [device['name'] for role in group['roles'] for device in role['devices']],
        "vars": group["data"],
    }
    for group in roleGroups
}

finalTenantGroups = {
    tenant["name"]: {
        "hosts": [device["name"] for device in tenant["devices"]],
        "vars": {
            "networks": {
                network["role"]["name"]: {
                    "is_pool": network["is_pool"],
                    "network": network["prefix"],
                }
                for network in tenant["networks"]
            }
        },
    }
    for tenant in tenantGroups
}

finalHosts = {
    "_meta": {
        "hostvars": {
            host.pop("name"): {
                "ansible_host": host["primary_ip4"]["address"]
                if host["primary_ip4"]
                else "",
                "device_serial": host["serial"] if host["serial"] else "",
            }
            for host in hosts
        }
    }
}

# pprint(finalEnclaveGroups)
# pprint(finalRoleGroups)
# pprint(finalTenantGroups)
# pprint(finalHosts)

inventory = {}
inventory.update(finalEnclaveGroups)
inventory.update(finalRoleGroups)
inventory.update(finalTenantGroups)
inventory.update(finalHosts)

print(json.dumps(inventory, indent=4, sort_keys=True))
