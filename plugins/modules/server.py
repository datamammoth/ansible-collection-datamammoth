#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Manage DataMammoth cloud servers."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: server
short_description: Manage DataMammoth cloud servers
description:
  - Create, delete, and manage power state of DataMammoth cloud servers.
  - Supports idempotent creation based on server name.
  - Polls asynchronous provisioning tasks until completion.
version_added: "0.1.0"
author: "DataMammoth <dev@datamammoth.com>"
options:
  name:
    description: Hostname / display name for the server.
    type: str
    required: true
  product:
    description: Product/plan slug (e.g. vps-medium, dedicated-large).
    type: str
  image:
    description: OS image slug (e.g. ubuntu-22.04, debian-12).
    type: str
  zone:
    description: Availability zone slug (e.g. us-east, eu-west).
    type: str
  state:
    description: Desired state of the server.
    type: str
    choices: [present, absent, running, stopped, restarted]
    default: present
  wait:
    description: Whether to wait for async operations to complete.
    type: bool
    default: true
  wait_timeout:
    description: Maximum seconds to wait for async operations.
    type: int
    default: 300
  api_key:
    description: DataMammoth API key. Can also use DM_API_KEY env var.
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
requirements: []
"""

EXAMPLES = r"""
- name: Create a VPS
  datamammoth.cloud.server:
    name: web-01
    product: vps-medium
    image: ubuntu-22.04
    zone: us-east
    state: present
    api_key: "{{ dm_api_key }}"
  register: server

- name: Stop a server
  datamammoth.cloud.server:
    name: web-01
    state: stopped
    api_key: "{{ dm_api_key }}"

- name: Delete a server
  datamammoth.cloud.server:
    name: web-01
    state: absent
    api_key: "{{ dm_api_key }}"
"""

RETURN = r"""
id:
  description: Server ID.
  type: str
  returned: when state != absent
ip_address:
  description: Primary IPv4 address.
  type: str
  returned: when state != absent
status:
  description: Current server status.
  type: str
  returned: always
server:
  description: Full server details dict.
  type: dict
  returned: when state != absent
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.datamammoth.cloud.plugins.module_utils.dm_api import (
    DM_COMMON_ARGS,
    DataMammothAPIError,
    get_client,
)


def find_server_by_name(client, name):
    """Find a server by hostname. Returns dict or None."""
    result = client.get(f"/servers?hostname={name}")
    servers = result.get("data", [])
    if isinstance(servers, list) and len(servers) > 0:
        return servers[0]
    return None


def create_server(module, client):
    """Create a new server and optionally wait for provisioning."""
    body = {
        "hostname": module.params["name"],
        "product_id": module.params["product"],
        "image_id": module.params["image"],
        "zone_id": module.params["zone"],
    }
    result = client.post("/servers", body)
    data = result.get("data", {})
    task_id = data.get("task_id")
    server_id = data.get("id")

    if task_id and module.params["wait"]:
        client.wait_for_task(task_id, timeout=module.params["wait_timeout"])

    if server_id:
        server = client.get(f"/servers/{server_id}").get("data", {})
        return server
    return data


def delete_server(module, client, server_id):
    """Delete a server and optionally wait for completion."""
    result = client.delete(f"/servers/{server_id}")
    task_id = result.get("data", {}).get("task_id")
    if task_id and module.params["wait"]:
        try:
            client.wait_for_task(task_id, timeout=module.params["wait_timeout"])
        except DataMammothAPIError:
            pass  # Task endpoint may 404 after deletion


def power_action(module, client, server_id, action):
    """Execute a power action on a server."""
    client.post(f"/servers/{server_id}/actions/{action}")
    if module.params["wait"]:
        import time
        deadline = time.time() + module.params["wait_timeout"]
        while time.time() < deadline:
            server = client.get(f"/servers/{server_id}").get("data", {})
            status = server.get("status", "")
            if action == "power-on" and status == "running":
                return server
            if action in ("power-off", "shutdown") and status == "stopped":
                return server
            if action == "reboot" and status == "running":
                return server
            time.sleep(5)
    return client.get(f"/servers/{server_id}").get("data", {})


def run_module():
    argument_spec = dict(
        name=dict(type="str", required=True),
        product=dict(type="str"),
        image=dict(type="str"),
        zone=dict(type="str"),
        state=dict(type="str", default="present", choices=["present", "absent", "running", "stopped", "restarted"]),
        wait=dict(type="bool", default=True),
        wait_timeout=dict(type="int", default=300),
        **DM_COMMON_ARGS,
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ("state", "present", ["product", "image", "zone"], True),
        ],
        supports_check_mode=True,
    )

    state = module.params["state"]
    changed = False

    try:
        client = get_client(module)
        existing = find_server_by_name(client, module.params["name"])

        if state == "absent":
            if existing:
                if module.check_mode:
                    module.exit_json(changed=True, status="deleted")
                delete_server(module, client, existing["id"])
                changed = True
            module.exit_json(changed=changed, status="deleted")

        if state == "present":
            if existing:
                module.exit_json(
                    changed=False,
                    id=existing.get("id"),
                    ip_address=existing.get("ip_address"),
                    status=existing.get("status"),
                    server=existing,
                )
            if module.check_mode:
                module.exit_json(changed=True, status="would_create")
            server = create_server(module, client)
            module.exit_json(
                changed=True,
                id=server.get("id"),
                ip_address=server.get("ip_address"),
                status=server.get("status"),
                server=server,
            )

        # Power states
        if not existing:
            module.fail_json(msg=f"Server '{module.params['name']}' not found")

        server_id = existing["id"]
        current_status = existing.get("status", "")

        if state == "running" and current_status != "running":
            if not module.check_mode:
                server = power_action(module, client, server_id, "power-on")
                module.exit_json(changed=True, id=server_id, status=server.get("status"), server=server)
            module.exit_json(changed=True, status="would_start")

        if state == "stopped" and current_status != "stopped":
            if not module.check_mode:
                server = power_action(module, client, server_id, "shutdown")
                module.exit_json(changed=True, id=server_id, status=server.get("status"), server=server)
            module.exit_json(changed=True, status="would_stop")

        if state == "restarted":
            if not module.check_mode:
                server = power_action(module, client, server_id, "reboot")
                module.exit_json(changed=True, id=server_id, status=server.get("status"), server=server)
            module.exit_json(changed=True, status="would_restart")

        # Already in desired state
        module.exit_json(
            changed=False,
            id=existing.get("id"),
            ip_address=existing.get("ip_address"),
            status=existing.get("status"),
            server=existing,
        )

    except DataMammothAPIError as e:
        module.fail_json(msg=str(e))


def main():
    run_module()


if __name__ == "__main__":
    main()
