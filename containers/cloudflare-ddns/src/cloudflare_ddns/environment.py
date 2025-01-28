import os
from functools import cached_property

from cloudflare_ddns.services.cloudflare_adapter import CloudflareAdapter
from cloudflare_ddns.services.external_ip import ExternalIPHandler


class ServiceProvider:

    @cached_property
    def api_token(self) -> str:
        return os.environ["TOKEN"]

    @cached_property
    def zone_id(self) -> str:
        return os.environ["ZONE_ID"]

    @cached_property
    def dns_name(self) -> str:
        return os.environ["DNS_NAME"]

    @cached_property
    def enable_proxy(self) -> bool:  # pragma: nocover
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
