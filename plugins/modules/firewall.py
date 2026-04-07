#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Manage DataMammoth server firewall rules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: firewall
short_description: Manage DataMammoth server firewall rules
description:
  - Configure firewall rules for a DataMammoth cloud server.
  - Replaces existing rules with the provided set (declarative).
  - Use state=absent to remove all firewall rules.
version_added: "0.1.0"
author: "DataMammoth <dev@datamammoth.com>"
options:
  server:
    description: Server ID to configure firewall rules for.
    type: str
    required: true
  rules:
    description: >
      List of firewall rules. Each rule is a dict with keys:
      action (accept/drop), protocol (tcp/udp/icmp), port (e.g. "80", "443", "22"),
      source (CIDR, default 0.0.0.0/0).
    type: list
    elements: dict
    default: []
  state:
    description: Whether the firewall rules should be present or absent.
    type: str
    choices: [present, absent]
    default: present
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
- name: Configure firewall rules
  datamammoth.cloud.firewall:
    server: srv_abc123
    rules:
      - action: accept
        protocol: tcp
        port: "80"
      - action: accept
        protocol: tcp
        port: "443"
      - action: accept
        protocol: tcp
        port: "22"
        source: "10.0.0.0/8"
    api_key: "{{ dm_api_key }}"

- name: Remove all firewall rules
  datamammoth.cloud.firewall:
    server: srv_abc123
    state: absent
    api_key: "{{ dm_api_key }}"
"""

RETURN = r"""
rules:
  description: The current firewall rules after the operation.
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


def normalize_rule(rule):
    """Normalize a firewall rule for comparison."""
    return {
        "action": rule.get("action", "accept"),
        "protocol": rule.get("protocol", "tcp"),
        "port": str(rule.get("port", "")),
        "source": rule.get("source", "0.0.0.0/0"),
    }


def rules_equal(current, desired):
    """Compare two lists of rules (order-independent)."""
    current_set = {tuple(sorted(normalize_rule(r).items())) for r in current}
    desired_set = {tuple(sorted(normalize_rule(r).items())) for r in desired}
    return current_set == desired_set


def run_module():
    argument_spec = dict(
        server=dict(type="str", required=True),
        rules=dict(type="list", elements="dict", default=[]),
        state=dict(type="str", default="present", choices=["present", "absent"]),
        **DM_COMMON_ARGS,
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    server_id = module.params["server"]
    state = module.params["state"]

    try:
        client = get_client(module)

        # Get current rules
        result = client.get(f"/servers/{server_id}/firewall")
        current_rules = result.get("data", {}).get("rules", [])

        if state == "absent":
            if not current_rules:
                module.exit_json(changed=False, rules=[])
            if module.check_mode:
                module.exit_json(changed=True, rules=[])
            client.put(f"/servers/{server_id}/firewall", {"rules": []})
            module.exit_json(changed=True, rules=[])

        # state == present
        desired_rules = [normalize_rule(r) for r in module.params["rules"]]

        if rules_equal(current_rules, desired_rules):
            module.exit_json(changed=False, rules=current_rules)

        if module.check_mode:
            module.exit_json(changed=True, rules=desired_rules)

        result = client.put(f"/servers/{server_id}/firewall", {"rules": desired_rules})
        final_rules = result.get("data", {}).get("rules", desired_rules)
        module.exit_json(changed=True, rules=final_rules)

    except DataMammothAPIError as e:
        module.fail_json(msg=str(e))


def main():
    run_module()


if __name__ == "__main__":
    main()
