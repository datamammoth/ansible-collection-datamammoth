#!/usr/bin/python
# -*- coding: utf-8 -*-

"""List DataMammoth products/plans."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: product_info
short_description: List DataMammoth products and plans
description:
  - Retrieve available products/plans from the DataMammoth catalog.
  - Optionally filter by category (vps, dedicated, storage).
version_added: "0.1.0"
author: "DataMammoth <dev@datamammoth.com>"
options:
  category:
    description: Filter by product category.
    type: str
    choices: [vps, dedicated, storage]
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
- name: List all products
  datamammoth.cloud.product_info:
    api_key: "{{ dm_api_key }}"
  register: products

- name: List VPS products only
  datamammoth.cloud.product_info:
    category: vps
    api_key: "{{ dm_api_key }}"
  register: vps_products
"""

RETURN = r"""
products:
  description: List of product details.
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
        category=dict(type="str", choices=["vps", "dedicated", "storage"]),
        **DM_COMMON_ARGS,
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    try:
        client = get_client(module)
        path = "/products"
        if module.params.get("category"):
            path += f"?category={module.params['category']}"
        result = client.get(path)
        products = result.get("data", [])
        module.exit_json(changed=False, products=products)

    except DataMammothAPIError as e:
        module.fail_json(msg=str(e))


def main():
    run_module()


if __name__ == "__main__":
    main()
