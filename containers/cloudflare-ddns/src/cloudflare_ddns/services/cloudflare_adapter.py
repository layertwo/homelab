from ipaddress import IPv4Address, IPv6Address
from typing import List, Optional, Union

from cloudflare import Cloudflare
from cloudflare.types.dns import Record

from cloudflare_ddns.utils import get_dns_record_type

IPAddress = Union[IPv4Address, IPv6Address]


class CloudflareAdapter:
    def __init__(self, api_token: str, zone_id: str) -> None:
        self._client = Cloudflare(api_token=api_token)
        self._zone_id = zone_id

    def get_dns_record(self, dns_name: str, record_type: str) -> List[Record]:
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
