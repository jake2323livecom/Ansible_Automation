#!/usr/bin/env python
import requests  # To perform the API queries
import json  # To format and display the final output
import urllib3  # To disable SSL warning below
import pynautobot


# disable SSL warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# User definable variables
netbox_url = "http://192.168.14.129:8000"
netbox_token = "0697aefb87c38120c64883ef231ded2b9f19838e"

enclaveQuery = """
{
  config_contexts {
    name
    data
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
nb = pynautobot.api(url=netbox_url, token=netbox_token)


def gqlAPI(query):
    return nb.graphql.query(query=query).json



enclaveVars = gqlAPI(enclaveQuery)
tenantVars = gqlAPI(tenantQuery)
hostVars = gqlAPI(hostQuery)


enclaveGroups = enclaveVars["data"]["config_contexts"]
tenantGroups = tenantVars["data"]["tenants"]
hosts = hostVars["data"]["_meta"]

finalEnclaveGroups = {
    group["name"]: {
        "hosts": [device["name"] for device in group["platforms"][0]["devices"]],
        "vars": group["data"],
    }
    for group in enclaveGroups
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
            }
            for network in tenant["networks"]
        },
    }
    for tenant in tenantGroups
}

finalHosts = {
    "_meta": {
        "hostvars": {
            host.pop("name"): {
                "ansible_host": host["primary_ip4"]["address"] if host["primary_ip4"] else "",
                "device_serial": host["serial"] if host["serial"] else ""
            }
            for host in hosts
        }
    }
}

# pprint(finalEnclaveGroups)
# pprint(finalTenantGroups)
# pprint(finalHosts)


inventory = {}
inventory.update(finalEnclaveGroups)
inventory.update(finalTenantGroups)
inventory.update(finalHosts)

print(json.dumps(inventory, indent=4, sort_keys=True))

