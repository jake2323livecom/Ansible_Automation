from pprint import pprint

roleGroups = [
    {
        "name": "routers",
        "data": {
            "required_ACLs": [1, 2]
        },
        "roles": [
            {"devices": []},
            {"devices": []},
            {"devices": []},
            {
                "devices": []
            },
            {
                "devices": [
                    {"name": "B-KL002-M-R"}
                ]
            },
            {
                "devices": [
                    {"name": "R-KL002-M-R"}
                ]
            },
        ],
        "platforms": [],
    },
    {
        "name": "switches",
        "data": {
          "required_ACLs": [
            1
          ]
        },
        "roles": [
          {
            "devices": [
              {
                "name": "R-KL002-M-SW"
              }
            ]
          }
        ],
        "platforms": []
      }
]
# step1 = [device['name'] for device in role['devices']]

# for group in roleGroups:
#     for role in group['roles']:
#         for device in role['devices']:
#             deviceDicts.append(device['name'])

finalRoleGroups = {
    group["name"]: {
        "hosts": [device['name'] for role in group['roles'] for device in role['devices']],
        "vars": group["data"],
    }
    for group in roleGroups
}

pprint(finalRoleGroups)
