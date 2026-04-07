"""Shared API client for DataMammoth Ansible modules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json
import time

from ansible.module_utils.urls import open_url
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError


DEFAULT_BASE_URL = "https://app.datamammoth.com/api/v2"
DEFAULT_TIMEOUT = 60


class DataMammothAPIError(Exception):
    """Raised when the DM API returns an error."""

    def __init__(self, status_code, message, body=None):
        self.status_code = status_code
        self.body = body
        super().__init__(f"API error {status_code}: {message}")


class DataMammothClient:
    """HTTP client for the DataMammoth REST API v2."""

    def __init__(self, api_key, base_url=None, timeout=None):
        self.api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout or DEFAULT_TIMEOUT

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method, path, data=None):
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode("utf-8") if data else None

        try:
            resp = open_url(
                url,
                method=method,
                headers=self._headers(),
                data=body,
                timeout=self.timeout,
                validate_certs=True,
            )
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}
        except HTTPError as e:
            content = e.read().decode("utf-8") if e.fp else ""
            try:
                body = json.loads(content)
            except (ValueError, TypeError):
                body = {"message": content}
            raise DataMammothAPIError(e.code, body.get("message", content), body)
        except URLError as e:
            raise DataMammothAPIError(0, str(e.reason))

    def get(self, path):
        return self._request("GET", path)

    def post(self, path, data=None):
        return self._request("POST", path, data)

    def patch(self, path, data=None):
        return self._request("PATCH", path, data)

    def put(self, path, data=None):
        return self._request("PUT", path, data)

    def delete(self, path):
        return self._request("DELETE", path)

    def wait_for_task(self, task_id, timeout=300, interval=5):
        """Poll a task until it completes or fails."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = self.get(f"/tasks/{task_id}")
            status = result.get("data", {}).get("status", "")
            if status == "completed":
                return result
            if status == "failed":
                error = result.get("data", {}).get("error", "Unknown error")
                raise DataMammothAPIError(0, f"Task {task_id} failed: {error}")
            time.sleep(interval)
        raise DataMammothAPIError(0, f"Task {task_id} timed out after {timeout}s")


def get_client(module):
    """Create a DataMammothClient from an Ansible module's params."""
    return DataMammothClient(
        api_key=module.params["api_key"],
        base_url=module.params.get("api_url"),
        timeout=module.params.get("api_timeout"),
    )


# Common argument spec shared by all modules
DM_COMMON_ARGS = dict(
    api_key=dict(type="str", required=True, no_log=True, fallback=(lambda: None,)),
    api_url=dict(type="str", default=DEFAULT_BASE_URL),
    api_timeout=dict(type="int", default=DEFAULT_TIMEOUT),
)
