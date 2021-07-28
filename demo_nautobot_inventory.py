#!/usr/bin/env python
import requests  # To perform the API queries
import json  # To format and display the final output
import urllib3  # To disable SSL warning below
import pynautobot
from pprint import pprint


# disable SSL warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# User definable variables
netbox_url = "https://demo.nautobot.com/"
netbox_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

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


enclaves = gqlAPI(enclaveQuery)
hosts = gqlAPI(hostQuery)


enclaveGroups = [ group for group in enclaves["data"]["config_contexts"] if group['platforms']]
hosts = hosts["data"]["_meta"]

finalEnclaveGroups = {
    group["name"]: {
        "hosts": [device["name"] for device in group["platforms"][0]["devices"] ],
        "vars": group["data"],
    }
    for group in enclaveGroups
}





# finalHosts = {
#     "_meta": {
#         "hostvars": {
#             host.pop("name"): {
#                 "ansible_host": host["primary_ip4"]["address"]
#                 if host["primary_ip4"]
#                 else "",
#                 "device_serial": host["serial"] if host["serial"] else "",
#             }
#             for host in hosts
#         }
#     }
# }

# pprint(finalEnclaveGroups)
# pprint(finalRoleGroups)
# pprint(finalTenantGroups)
# pprint(finalHosts)

inventory = {}
inventory.update(finalEnclaveGroups)
# inventory.update(finalHosts)

print(json.dumps(inventory, indent=4, sort_keys=True))
