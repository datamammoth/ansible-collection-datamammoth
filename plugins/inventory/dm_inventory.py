#!/usr/bin/python
# -*- coding: utf-8 -*-

"""DataMammoth dynamic inventory plugin for Ansible."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
name: dm_inventory
plugin_type: inventory
short_description: DataMammoth dynamic inventory
description:
  - Fetches running servers from the DataMammoth API and builds an Ansible inventory.
  - Groups servers by zone, status, and product category.
  - Uses server IP address as the ansible_host.
version_added: "0.1.0"
author: "DataMammoth <dev@datamammoth.com>"
options:
  api_key:
    description: DataMammoth API key. Falls back to DM_API_KEY env var.
    type: str
    required: true
    env:
      - name: DM_API_KEY
  api_url:
    description: API base URL.
    type: str
    default: https://app.datamammoth.com/api/v2
    env:
      - name: DM_API_URL
  groups_by:
    description: Attributes to group hosts by.
    type: list
    elements: str
    default: [zone_id, status, product_id]
  running_only:
    description: Only include servers with status 'running'.
    type: bool
    default: false
"""

EXAMPLES = r"""
# datamammoth.yml
plugin: datamammoth.cloud.dm_inventory
api_key: "{{ lookup('env', 'DM_API_KEY') }}"
running_only: true
groups_by:
  - zone_id
  - status
"""

import json
import os

from ansible.plugins.inventory import BaseInventoryPlugin, Constructable
from ansible.errors import AnsibleError

try:
    from ansible.module_utils.urls import open_url
    HAS_OPEN_URL = True
except ImportError:
    HAS_OPEN_URL = False


class InventoryModule(BaseInventoryPlugin, Constructable):
    NAME = "datamammoth.cloud.dm_inventory"

    def verify_file(self, path):
        """Verify this is a valid inventory source."""
        valid = False
        if super().verify_file(path):
            if path.endswith(("datamammoth.yml", "datamammoth.yaml", "dm_inventory.yml", "dm_inventory.yaml")):
                valid = True
        return valid

    def parse(self, inventory, loader, path, cache=True):
        super().parse(inventory, loader, path, cache)
        self._read_config_data(path)

        api_key = self.get_option("api_key") or os.environ.get("DM_API_KEY")
        if not api_key:
            raise AnsibleError("api_key is required. Set it in the inventory file or DM_API_KEY env var.")

        api_url = (self.get_option("api_url") or "https://app.datamammoth.com/api/v2").rstrip("/")
        running_only = self.get_option("running_only")
        groups_by = self.get_option("groups_by") or ["zone_id", "status"]

        # Fetch servers
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            resp = open_url(f"{api_url}/servers", headers=headers, timeout=60)
            data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            raise AnsibleError(f"Failed to fetch servers from DataMammoth API: {e}")

        servers = data.get("data", [])

        for server in servers:
            status = server.get("status", "")
            if running_only and status != "running":
                continue

            hostname = server.get("hostname", server.get("id", "unknown"))
            ip_address = server.get("ip_address")

            if not ip_address:
                continue

            # Sanitize hostname for Ansible (replace dots/special chars)
            safe_name = hostname.replace(".", "_").replace("-", "_")
            self.inventory.add_host(safe_name)
            self.inventory.set_variable(safe_name, "ansible_host", ip_address)
            self.inventory.set_variable(safe_name, "dm_id", server.get("id"))
            self.inventory.set_variable(safe_name, "dm_hostname", hostname)
            self.inventory.set_variable(safe_name, "dm_status", status)
            self.inventory.set_variable(safe_name, "dm_zone", server.get("zone_id"))
            self.inventory.set_variable(safe_name, "dm_product", server.get("product_id"))
            self.inventory.set_variable(safe_name, "dm_image", server.get("image_id"))
            self.inventory.set_variable(safe_name, "dm_ip", ip_address)
            self.inventory.set_variable(safe_name, "dm_cpu", server.get("cpu"))
            self.inventory.set_variable(safe_name, "dm_memory", server.get("memory"))
            self.inventory.set_variable(safe_name, "dm_disk", server.get("disk"))

            # Group by attributes
            for attr in groups_by:
                value = server.get(attr)
                if value:
                    group_name = f"dm_{attr}_{str(value).replace('-', '_').replace('.', '_')}"
                    self.inventory.add_group(group_name)
                    self.inventory.add_child(group_name, safe_name)

            # Always add to 'datamammoth' group
            self.inventory.add_group("datamammoth")
            self.inventory.add_child("datamammoth", safe_name)
