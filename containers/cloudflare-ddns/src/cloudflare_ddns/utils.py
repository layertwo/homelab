from functools import lru_cache
from ipaddress import IPv4Address, IPv6Address
from typing import Any, Dict, Union

IPAddress = Union[IPv4Address, IPv6Address]
JsonDict = Dict[str, Any]


@lru_cache
def get_dns_record_type(ip: IPAddress) -> str:
    return "A" if ip.version == 4 else "AAAA"
