#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Get DataMammoth server information."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: server_info
short_description: Get DataMammoth server information
description:
  - Retrieve details about one or all DataMammoth cloud servers.
  - Can filter by server ID or hostname.
version_added: "0.1.0"
author: "DataMammoth <dev@datamammoth.com>"
options:
  id:
    description: Server ID to look up. Mutually exclusive with name.
    type: str
  name:
    description: Server hostname to look up. Mutually exclusive with id.
    type: str
  api_key:
    description: DataMammoth API key.
    type: str
    required: true
  api_url:
    description: API base URL.
    type: str
    default: https://app.datamammoth.com/api/v2
  api_timeout:
    description: HTTP request timeout in seconds.
    type: int
    default: 60
"""

EXAMPLES = r"""
- name: Get all servers
  datamammoth.cloud.server_info:
    api_key: "{{ dm_api_key }}"
  register: all_servers

- name: Get a specific server by ID
  datamammoth.cloud.server_info:
    id: srv_abc123
    api_key: "{{ dm_api_key }}"
  register: server

- name: Get a specific server by name
  datamammoth.cloud.server_info:
    name: web-01
    api_key: "{{ dm_api_key }}"
  register: server
"""

RETURN = r"""
servers:
  description: List of server details.
  type: list
  elements: dict
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.datamammoth.cloud.plugins.module_utils.dm_api import (
    DM_COMMON_ARGS,
    DataMammothAPIError,
    get_client,
)


def run_module():
    argument_spec = dict(
        id=dict(type="str"),
        name=dict(type="str"),
        **DM_COMMON_ARGS,
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[("id", "name")],
        supports_check_mode=True,
    )

    try:
        client = get_client(module)

        if module.params["id"]:
            result = client.get(f"/servers/{module.params['id']}")
            servers = [result.get("data", {})]
        elif module.params["name"]:
            result = client.get(f"/servers?hostname={module.params['name']}")
            servers = result.get("data", [])
        else:
            result = client.get("/servers")
            servers = result.get("data", [])

        module.exit_json(changed=False, servers=servers)

    except DataMammothAPIError as e:
        module.fail_json(msg=str(e))


def main():
    run_module()


if __name__ == "__main__":
    main()
