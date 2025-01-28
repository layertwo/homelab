from functools import cached_property
from ipaddress import ip_address

import requests

from cloudflare_ddns.utils import IPAddress, JsonDict


class ExternalIPHandler:
    def _get(self) -> JsonDict:
        response = requests.get(
            "https://ifconfig.co/json", headers={"Content-Type": "application/json"}
        )
        return response.json()

    @cached_property
    def ip(self) -> IPAddress:
        data = self._get()
        return ip_address(data["ip"])
