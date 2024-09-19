import os
from functools import cached_property, lru_cache
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Any, Dict, Optional, Union

import requests
from cloudflare import Cloudflare
from cloudflare.types.dns import Record

JsonDict = Dict[str, Any]
IPAddress = Union[IPv4Address, IPv6Address]


class ExternalIPHandler:

    def _get(self) -> JsonDict:
        resp = requests.get(
            "https://ifconfig.co/json", headers={"Content-Type": "application/json"}
        )
        return resp.json()

    @cached_property
    def ip(self) -> IPAddress:
        data = self._get()
        return ip_address(data["ip"])


class CloudflareAdapter:
    def __init__(self, api_token: str, zone_id: str) -> None:
        self._client = Cloudflare(api_token=api_token)
        self._zone_id = zone_id

    def get_dns_record(self, dns_name: str, record_type: str) -> Optional[Record]:
        return self._client.dns.records.list(
            zone_id=self._zone_id, name=dns_name, match="all", type=record_type
        )

    def create_dns_record(
        self,
        dns_name: str,
        ip: IPAddress,
        enable_proxy: bool = False,
    ) -> Optional[Record]:
        return self._client.dns.records.create(
            zone_id=self._zone_id,
            name=dns_name,
            type=get_dns_record_type(ip),
            content=str(ip),
            proxied=enable_proxy,
        )

    def update_dns_record(
        self,
        record_id: str,
        dns_name: str,
        ip: IPAddress,
        enable_proxy: bool = False,
    ) -> Optional[Record]:
        return self._client.dns.records.update(
            dns_record_id=record_id,
            zone_id=self._zone_id,
            name=dns_name,
            type=get_dns_record_type(ip),
            content=str(ip),
            proxied=enable_proxy,
        )


@lru_cache
def get_dns_record_type(ip: IPAddress) -> str:
    return "A" if ip.version == 4 else "AAAA"


class ServiceProvider:
    @cached_property
    def api_token(self) -> str:
        return os.environ.get("TOKEN")

    @cached_property
    def zone_id(self) -> str:
        return os.environ.get("ZONE_ID")

    @cached_property
    def dns_name(self) -> str:
        return os.environ.get("DNS_NAME")

    @cached_property
    def enable_proxy(self) -> bool:
        val = os.environ.get("ENABLE_PROXY", "false")
        if val.lower() == "true":
            return True
        elif val.lower() == "false":
            return False
        print(f"Invalid value ({val}) for ENABLE_PROXY")
        return False

    @cached_property
    def external_ip_handler(self) -> ExternalIPHandler:
        return ExternalIPHandler()

    @cached_property
    def cloudflare_adapter(self) -> CloudflareAdapter:
        return CloudflareAdapter(api_token=self.api_token, zone_id=self.zone_id)


def main():
    sp = ServiceProvider()
    e = sp.external_ip_handler
    cf = sp.cloudflare_adapter

    record_type = get_dns_record_type(e.ip)
    records = cf.get_dns_record(dns_name=sp.dns_name, record_type=record_type)

    if not records:
        record = cf.create_dns_record(
            dns_name=sp.dns_name, ip=e.ip, enable_proxy=sp.enable_proxy
        )
    else:
        for record in records:
            old_address = record.content
            old_record_type = record.type

            if old_record_type not in ["A", "AAAA"]:
                # we only deal with A / AAAA records
                continue

            if record_type != old_record_type:
                print(
                    f"wrong address family type for {sp.dns_name} / {old_address} / {old_record_type}"
                )
                continue

            if e.ip == ip_address(old_address):
                if sp.enable_proxy == record.proxied:
                    print(f"nothing to update for {sp.dns_name} / {old_address}")
                    continue
                print(
                    f"updating proxy for record {sp.dns_name} / {e.ip} to {sp.enable_proxy}"
                )

            cf.update_dns_record(
                record_id=record.id,
                dns_name=sp.dns_name,
                ip=e.ip,
                enable_proxy=sp.enable_proxy,
            )


if __name__ == "__main__":
    main()
