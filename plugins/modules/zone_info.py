#!/usr/bin/python
# -*- coding: utf-8 -*-

"""List DataMammoth availability zones."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: zone_info
short_description: List DataMammoth availability zones
description:
  - Retrieve available availability zones from the DataMammoth API.
version_added: "0.1.0"
author: "DataMammoth <dev@datamammoth.com>"
options:
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
- name: List all zones
  datamammoth.cloud.zone_info:
    api_key: "{{ dm_api_key }}"
  register: zones

- name: Show zone names
  debug:
    msg: "{{ zones.zones | map(attribute='name') | list }}"
"""

RETURN = r"""
zones:
  description: List of availability zone details.
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
    argument_spec = dict(**DM_COMMON_ARGS)

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    try:
        client = get_client(module)
        result = client.get("/zones")
        zones = result.get("data", [])
        module.exit_json(changed=False, zones=zones)

    except DataMammothAPIError as e:
        module.fail_json(msg=str(e))


def main():
    run_module()


if __name__ == "__main__":
    main()
