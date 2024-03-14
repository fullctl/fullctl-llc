try:
    from django.conf import settings

    DEFAULT_NETBOX_TOKEN = getattr(settings, "NETBOX_TOKEN", "")
except ImportError:
    DEFAULT_NETBOX_TOKEN = ""

from fullctl.service_bridge.client import Bridge, DataObject
from fullctl.service_bridge.context import service_bridge_context

CACHE = {}


class NetboxObject(DataObject):
    source = "netbox"
    description = "Netbox Object"


class Netbox(Bridge):

    """
    Service bridge for netbox data retrieval
    """

    url_prefix = ""
    results_key = "results"

    class Meta:
        service = "netbox"
        ref_tag = "base"
        data_object_cls = NetboxObject

    def __init__(self, key=None, org=None, **kwargs):
        url = getattr(settings, "NETBOX_URL", None)

        ctx = service_bridge_context.get()
        svc = ctx.get_service("netbox")

        if svc:
            url = svc.service_url
            if svc.federated and not key:
                key = getattr(svc.config, "API_TOKEN", None)
                if not key:
                    raise AttributeError(
                        "netbox API_TOKEN not set on federated service not"
                    )

        if not key:
            key = DEFAULT_NETBOX_TOKEN

        kwargs.setdefault("cache_duration", 10)
        kwargs.setdefault("cache", CACHE)

        if not url:
            raise AttributeError("netbox url not set / federated service not found")

        if not key:
            raise AttributeError("netbox key not set / federated service not found")

        super().__init__(url, key, org, **kwargs)

    @property
    def auth_headers(self):
        return {"Authorization": f"Token {self.key}"}

    def ux_url(self, id):
        return f"{self.host}/{self.ref_tag}/{id}/?tab=main"


class DeviceTypeObject(NetboxObject):
    description = "Netbox Device Type"


class DeviceType(Netbox):
    class Meta(Netbox.Meta):
        ref_tag = "dcim/device-types"
        data_object_cls = DeviceTypeObject


class DeviceObject(NetboxObject):
    description = "Netbox Device"


class Device(Netbox):
    class Meta(Netbox.Meta):
        ref_tag = "dcim/devices"
        data_object_cls = DeviceObject


class InterfaceObject(NetboxObject):
    description = "Netbox Interface"


class Interface(Netbox):
    class Meta(Netbox.Meta):
        ref_tag = "dcim/interfaces"
        data_object_cls = InterfaceObject


class IPAddressObject(NetboxObject):
    description = "Netbox IP-Address"


class IPAddress(Netbox):
    class Meta(Netbox.Meta):
        ref_tag = "ipam/ip-addresses"
        data_object_cls = IPAddressObject


class VLANObject(NetboxObject):
    description = "Netbox VLAN"


class VLAN(Netbox):
    class Meta(Netbox.Meta):
        ref_tag = "ipam/vlans"
        data_object_cls = VLANObject


class PrefixObject(NetboxObject):
    description = "Netbox Prefix"


class Prefix(Netbox):
    class Meta(Netbox.Meta):
        ref_tag = "ipam/prefixes"
        data_object_cls = PrefixObject


class SiteObject(NetboxObject):
    description = "Netbox Site"


class Site(Netbox):
    class Meta(Netbox.Meta):
        ref_tag = "dcim/sites"
        data_object_cls = SiteObject


class CustomFieldObject(NetboxObject):
    description = "Netbox CustomField"


class CustomField(Netbox):
    class Meta(Netbox.Meta):
        ref_tag = "extras/custom-fields"
        data_object_cls = CustomFieldObject

    def sync(self, fields):
        netbox_fields = {nbf.name: nbf for nbf in self.objects()}

        for field in fields:
            netbox_field = netbox_fields.get(field["name"])

            if not netbox_field:
                self.create(field)
            else:
                self.update(netbox_field, field)
