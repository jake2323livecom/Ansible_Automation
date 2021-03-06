#!/usr/bin/env python
import requests  # To perform the API queries
import json  # To format and display the final output
import urllib3  # To disable SSL warning below
import ipaddress  # To get the network id without having to do an API call to find it

# disable SSL warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# User definable variables
netbox_url = "http://192.168.88.131"
netbox_token = "1ec7f6872d96e73f885a97f1ed190a88b0a5f5ca"
# Define what you want to group devices by.
# Ensure they are variables found in the devices API and not somewhere else.
group_by = ["sites", "tenant", "rack", "model"]
# This will need to be changed to Jbn when moved up to JDI
enclave = "Black"
# Filter by the following site:
# site = os.environ['group']
group = "exped"
site = "exped"
# ------------------------------------------------------------------------------------
# You shouldn't have to modify below this line
# ------------------------------------------------------------------------------------
header = {
    "Accept": "application/json; indent=4",
    "Content-Type": "application/json",
    "Authorization": "Token " + netbox_token,
}

# We are performing 3 seperate API calls
devices_api = "/api/dcim/devices/"
interfaces_api = "/api/dcim/interfaces/"
ip_addresses_api = "/api/ipam/ip-addresses/"
platforms_api = "/api/dcim/platforms/"
prefixes_api = "/api/ipam/prefixes/"

# In order for the limit=0 to work, you must modify the MAX_PAGE_SIZE=0 in your configuration.py
# in the /opt/netbox/netbox/netbox/configuration.py on the netbox server
netbox_query = "?format=json&limit=0&site=" + site

# Do the actual API calls
devices_get = requests.get(
    netbox_url + devices_api + netbox_query, headers=header, verify=False
).json()
interfaces_get = requests.get(
    netbox_url + interfaces_api + netbox_query, headers=header, verify=False
).json()
ip_addresses_get = requests.get(
    netbox_url + ip_addresses_api + netbox_query, headers=header, verify=False
).json()
platforms_get = requests.get(
    netbox_url + platforms_api + netbox_query, headers=header, verify=False
).json()
prefixes_get = requests.get(
    netbox_url + prefixes_api + netbox_query, headers=header, verify=False
).json()

# First build our device list IF it has a primary_ip set
hostvars = {}
for dev in devices_get["results"]:
    # Unpack tags from the new data model
    tags = [tag['name'] for tag in dev['tags']]

    # if dev['primary_ip'] is not None:
    # This can be enabled if/when you want to only include devices with a primary IP
    hostvars[dev["name"]] = {
        # 'ansible_host': str(ipaddress.IPv4Interface(dev['primary_ip']['address']).ip)
        # This can be enabled if/when you want to only include devices with a primary IP
        "device_type": dev["device_type"]["model"],  # Required
        "device_role": dev["device_role"][
            "name"
        ],  # Required hostsvars['KL001-R'] = {"device_type": dev["device_type"]["model"]}
        "site": dev["site"]["name"],  # Required
        "model": dev["device_type"]["model"],  # Required
        "enclave": tags,  # Formerly known as "enclave"
        "interfaces": {},  # placeholder for later
    }
    # Add config context variables without the config_context key
    hostvars[dev["name"]].update(dev["config_context"])

    # Not every device has a primary_ip assigned but we will add it to ansible anyway for now.
    # Eventually these should go away and re-enable the 2 lines above
    if dev["primary_ip"]:
        hostvars[dev["name"]]["ansible_host"] = str(
            ipaddress.IPv4Interface(dev["primary_ip"]["address"]).ip
        )
    # This is only done in NTS to allow for b_ templates to work. This will be commented out in production
    if enclave in tags:
        hostvars[dev["name"]]["device_type"] = "b_" + dev["device_type"]["model"]
    # These next fields are not required.
    # But because they need sub data (IE: Name) we can't do the same thing as config_context above.
    if dev["rack"]:  # if this device has a rack, add it to the dictionary
        hostvars[dev["name"]]["rack"] = dev["rack"]["name"]
    if dev["tenant"]:
        hostvars[dev["name"]]["tenant"] = dev["tenant"]["name"]
    if dev["platform"]:
        hostvars[dev["name"]]["platform"] = dev["platform"]["name"]

        # If the device's platform uses the ios napalm driver
        # then we need to add ansible vars to be able to interact with the device.
        if (
            next(
                item
                for item in platforms_get["results"]
                if item["name"] == dev["platform"]["name"]
            )["napalm_driver"]
            == "ios"
        ):
            hostvars[dev["name"]].update(
                {
                    "ansible_become": "yes",
                    "ansible_become_method": "enable",
                    "ansible_connection": "network_cli",
                    "ansible_network_os": "ios",
                }
            )

# Now for each interface, if its in our device list, add all of its interfaces
for interfaces in interfaces_get["results"]:
    # Unpack the interface tags dictionary
    tags = [tag["name"] for tag in interfaces["tags"]]

    if interfaces["device"]["display_name"] in hostvars:
        hostvars[
            interfaces["device"][
                "display_name"
            ]  # update the hostvars where the interface device display name is
        ]["interfaces"][interfaces["name"]] = {
            "description": interfaces["description"],
            "mac_address": interfaces["mac_address"],
            "mtu": interfaces["mtu"],
            "lag": interfaces["lag"],
            "tagged_vlans": [],  # placeholder for later
            "tags": tags,
        }

        # Add ISP_tun_source if ISP in tags:
        if "ISP_tun_source" in tags:
            hostvars[interfaces["device"]["display_name"]].update(
                {"ISP_tunnel_source": interfaces["name"]}
            )

        # Add the sipr and regular tunnel source variables if tagged:
        if "tun_source" in tags:
            hostvars[interfaces["device"]["display_name"]].update(
                {"tunnel_source": interfaces["name"]}
            )

        if "sipr_tun_source" in tags:
            hostvars[interfaces["device"]["display_name"]].update(
                {"sipr_tunnel_source": interfaces["name"]}
            )

        # Adding JBNCT_variable
        if "JBNCT" in tags:
            hostvars[interfaces["device"]["display_name"]].update(
                {"JBNCT": interfaces["name"]}
            )

        # These next fields are not required.
        # But because they need sub data (IE: Name) or can be null we can't do the same thing as above.
        if interfaces["mode"]:
            hostvars[interfaces["device"]["display_name"]]["interfaces"][
                interfaces["name"]
            ]["mode"] = interfaces["mode"]["label"]

        if interfaces["untagged_vlan"]:
            hostvars[interfaces["device"]["display_name"]]["interfaces"][
                interfaces["name"]
            ]["untagged_vlan"] = interfaces["untagged_vlan"]["vid"]

        if interfaces["tagged_vlans"]:
            for vid in interfaces["tagged_vlans"]:
                hostvars[interfaces["device"]["display_name"]]["interfaces"][
                    interfaces["name"]
                ]["tagged_vlans"].append(vid["vid"])

# Finally assign each host's interface with its IP, if its set.
for ip in ip_addresses_get["results"]:
    # Unpack the IP tags
    tags = [tag["name"] for tag in ip["tags"]]

    # If the try fails its because its a static IP and not associated to an interface
    try:
        # Assign host and interface variables
        host = ip["assigned_object"]["device"]["name"]
        interface = ip["assigned_object"]["name"]

        if host in hostvars:
            # Not sure if all of these are needed, but better to do the math in python than ansible
            # Print just the IP, remove the mask
            hostvars[host]["interfaces"][interface]["ip"] = str(
                ipaddress.IPv4Interface(ip["address"]).ip
            )
            # Now just the full doted decimal notation of the subnet mask
            hostvars[host]["interfaces"][ip["assigned_object"]["name"]][
                "netmask"
            ] = str(ipaddress.IPv4Interface(ip["address"]).with_netmask.split("/")[1])
            # Now just the full doted decimal notation of the hostmask
            hostvars[host]["interfaces"][interface]["hostmask"] = str(
                ipaddress.IPv4Interface(ip["address"]).with_hostmask.split("/")[1]
            )
            # Find the network ID based off the IP/Mask
            hostvars[host]["interfaces"][interface]["netid"] = str(
                ipaddress.IPv4Interface(ip["address"]).network
            )
            # Now use the netid and mask to determine the broadcast address
            hostvars[host]["interfaces"][interface]["broadcast"] = str(
                ipaddress.IPv4Network(
                    ipaddress.IPv4Interface(
                        ipaddress.IPv4Interface(ip["address"]).network
                    )
                ).broadcast_address
            )

            # Add the manet_ip if MANET is in the ip tags
            if "MANET" in tags:
                hostvars[host].update(
                    {"manet_ip_addr": str(ipaddress.IPv4Interface(ip["address"]).ip)}
                )
    except:
        pass

# Now to group everything based off the list above.
# REMEMBER, this is based off the host data, NOT interface data.
groups = {}
for host in hostvars:
    # Setting a variable so we don't have to loop again later.
    # If the host gets added to a group, then don't add it to the ungrouped group.
    found = False
    for group in group_by:
        # Adding try just in case you want to group by something that isn't defined for that particular host.
        # IE: rack, tenant or platform
        try:
            if hostvars[host][group]:
                found = True
                groups.setdefault(hostvars[host][group], {"hosts": []}).update()
                groups[hostvars[host][group]]["hosts"].append(host)
                # Now add the hostname to the hosts section for each group
        except:
            pass
    if found == False:
        groups.setdefault("ungrouped", {"hosts": []}).update()
        groups["ungrouped"]["hosts"].append(host)

# Add prefixes (Subnets) to groupvars
for subnet in prefixes_get["results"]:
    # If the subnet has a tenant name in groups:
    if subnet["tenant"] and subnet["tenant"]["name"] in groups.keys():

        # Add vars if not present
        groups.get(subnet["tenant"]["name"]).setdefault("vars", {})
        # groups[subnet["tenant"]["name"]]["vars"].setdefault("required_pools", [])

        # Add networks to vars if not present
        groups[subnet["tenant"]["name"]]["vars"].setdefault("networks", {})

        # Add each network description as key, network (cidr) and is_pool
        groups[subnet["tenant"]["name"]]["vars"]["networks"].update(
            {
                subnet["description"]: {
                    "network": subnet["prefix"],
                    "is_pool": subnet["is_pool"],
                }
            }
        )

        # Add the network to required_pools if "is_pool"
        # if subnet["is_pool"]:
        #     groups[subnet["tenant"]["name"]]["vars"]["required_pools"].append(subnet["description"])

# Some quick queries for debug purposes
# print(json.dumps(hostvars['blackout.marvel'], indent=4))
# print(json.dumps(hostvars['ISP-101-ExtRtr-114'], indent=4))
# print(json.dumps(groups, indent=4))

# Final step, create one dictionary with both the groups and hostvars data and display it to the screen
# First we have to add the _meta and hostvars to the dictionary to apeas ansible
final_host_list = {"_meta": {"hostvars": hostvars}}
# Now combine them. We could just pikc one and update it,
# but this way its non-destructive so we can still debug later if need be.
overall_list = {}
overall_list.update(groups)
overall_list.update(final_host_list)
print(json.dumps(overall_list, indent=4, sort_keys=True))
