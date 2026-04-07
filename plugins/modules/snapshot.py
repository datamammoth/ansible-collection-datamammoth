#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Manage DataMammoth server snapshots."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: snapshot
short_description: Manage DataMammoth server snapshots
description:
  - Create and delete snapshots of DataMammoth cloud servers.
  - Snapshots are immutable; updating is not supported.
version_added: "0.1.0"
author: "DataMammoth <dev@datamammoth.com>"
options:
  server:
    description: Server ID to create/delete snapshot for.
    type: str
    required: true
  name:
    description: Name of the snapshot. Required when state=present.
    type: str
  snapshot_id:
    description: Snapshot ID. Required when state=absent.
    type: str
  state:
    description: Desired state.
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
- name: Create a snapshot
  datamammoth.cloud.snapshot:
    server: srv_abc123
    name: pre-deploy-backup
    state: present
    api_key: "{{ dm_api_key }}"
  register: snap

- name: Delete a snapshot
  datamammoth.cloud.snapshot:
    server: srv_abc123
    snapshot_id: snap_xyz789
    state: absent
    api_key: "{{ dm_api_key }}"
"""

RETURN = r"""
id:
  description: Snapshot ID.
  type: str
  returned: when state=present
snapshot:
  description: Full snapshot details.
  type: dict
  returned: when state=present
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.datamammoth.cloud.plugins.module_utils.dm_api import (
    DM_COMMON_ARGS,
    DataMammothAPIError,
    get_client,
)


def run_module():
    argument_spec = dict(
        server=dict(type="str", required=True),
        name=dict(type="str"),
        snapshot_id=dict(type="str"),
        state=dict(type="str", default="present", choices=["present", "absent"]),
        **DM_COMMON_ARGS,
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ("state", "present", ["name"]),
            ("state", "absent", ["snapshot_id"]),
        ],
        supports_check_mode=True,
    )

    server_id = module.params["server"]
    state = module.params["state"]

    try:
        client = get_client(module)

        if state == "present":
            if module.check_mode:
                module.exit_json(changed=True)
            result = client.post(f"/servers/{server_id}/snapshots", {"name": module.params["name"]})
            data = result.get("data", {})
            module.exit_json(
                changed=True,
                id=data.get("id"),
                snapshot=data,
            )

        if state == "absent":
            snapshot_id = module.params["snapshot_id"]
            if module.check_mode:
                module.exit_json(changed=True)
            try:
                client.delete(f"/servers/{server_id}/snapshots/{snapshot_id}")
                module.exit_json(changed=True)
            except DataMammothAPIError as e:
                if e.status_code == 404:
                    module.exit_json(changed=False)
                raise

    except DataMammothAPIError as e:
        module.fail_json(msg=str(e))


def main():
    run_module()


if __name__ == "__main__":
    main()
