# Ansible Collection for DataMammoth

Automate DataMammoth server provisioning and management with Ansible.

> **Status**: Under development. Not yet published to Ansible Galaxy.

## Installation

```bash
ansible-galaxy collection install datamammoth.cloud
```

## Example Playbooks

### Provision a Server

```yaml
---
- name: Provision a web server
  hosts: localhost
  connection: local
  collections:
    - datamammoth.cloud

  vars:
    dm_api_key: "{{ lookup('env', 'DM_API_KEY') }}"

  tasks:
    - name: Create a VPS instance
      datamammoth_server:
        api_key: "{{ dm_api_key }}"
        hostname: "web-01"
        product_id: "prod_abc"
        image_id: "img_ubuntu2204"
        region: "eu-central-1"
        state: present
      register: server

    - name: Display server IP
      debug:
        msg: "Server IP: {{ server.ip_address }}"

    - name: Add to inventory
      add_host:
        name: "{{ server.ip_address }}"
        groups: webservers
```

### Manage Firewall Rules

```yaml
- name: Configure firewall
  hosts: localhost
  connection: local
  collections:
    - datamammoth.cloud

  tasks:
    - name: Allow SSH
      datamammoth_firewall_rule:
        api_key: "{{ dm_api_key }}"
        server_id: "{{ server_id }}"
        protocol: tcp
        port: 22
        source: "0.0.0.0/0"
        action: allow

    - name: Allow HTTP/HTTPS
      datamammoth_firewall_rule:
        api_key: "{{ dm_api_key }}"
        server_id: "{{ server_id }}"
        protocol: tcp
        port: "{{ item }}"
        source: "0.0.0.0/0"
        action: allow
      loop:
        - 80
        - 443
```

### Create a Snapshot

```yaml
- name: Snapshot before upgrade
  hosts: localhost
  connection: local
  collections:
    - datamammoth.cloud

  tasks:
    - name: Create snapshot
      datamammoth_snapshot:
        api_key: "{{ dm_api_key }}"
        server_id: "{{ server_id }}"
        name: "pre-upgrade-{{ ansible_date_time.date }}"
        state: present
```

## Modules

| Module | Description |
|--------|-------------|
| `datamammoth_server` | Create, update, delete servers |
| `datamammoth_server_info` | Gather server facts |
| `datamammoth_firewall_rule` | Manage firewall rules |
| `datamammoth_dns_zone` | Manage DNS zones |
| `datamammoth_dns_record` | Manage DNS records |
| `datamammoth_snapshot` | Manage server snapshots |
| `datamammoth_ssh_key` | Manage SSH keys |

## Documentation

- [API Reference](https://data-mammoth.com/api-docs/reference)
- [Getting Started Guide](https://data-mammoth.com/api-docs/guides)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
