from ipaddress import ip_address
from typing import Optional

from cloudflare_ddns.environment import ServiceProvider
from cloudflare_ddns.utils import get_dns_record_type


def main(service_provider: Optional[ServiceProvider] = None) -> None:
    if service_provider is None:  # pragma: nocover
        service_provider = ServiceProvider()

    cf = service_provider.cloudflare_adapter
    ip_handler = service_provider.external_ip_handler
    external_ip = ip_handler.ip
    dns_name = service_provider.dns_name
    enable_proxy = service_provider.enable_proxy

    record_type = get_dns_record_type(external_ip)
    records = cf.get_dns_record(dns_name=service_provider.dns_name, record_type=record_type)

    if not records:
        print(f"record not found, creating record {dns_name} with ip {external_ip}")
        record = cf.create_dns_record(dns_name=dns_name, ip=external_ip, enable_proxy=enable_proxy)
    else:
        for record in records:
            old_external_ip = record.content
            old_record_type = record.type

            if old_record_type not in ["A", "AAAA"]:
                # we only deal with A / AAAA records
                continue

            if record_type != old_record_type:
                print(
                    f"wrong address family type for {dns_name} / {old_external_ip} / {old_record_type}"
                )
                continue

            if external_ip == ip_address(old_external_ip):
                if enable_proxy == record.proxied:
                    print(f"nothing to update for {dns_name} / {old_external_ip}")
                    continue
                else:
                    print(f"updating proxy for record {dns_name} / {external_ip} to {enable_proxy}")
            else:
                print(f"updating record for {dns_name} from {old_external_ip} to {external_ip}")

            cf.update_dns_record(
                record_id=record.id,
                dns_name=dns_name,
                ip=external_ip,
                enable_proxy=enable_proxy,
            )
