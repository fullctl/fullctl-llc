try:
    from django.conf import settings

    DEFAULT_NAUTOBOT_TOKEN = settings.NAUTOBOT_TOKEN
except ImportError:
    DEFAULT_NAUTOBOT_TOKEN = ""

from fullctl.service_bridge.client import Bridge, DataObject

CACHE = {}


class NautobotObject(DataObject):
    source = "nautobot"
    description = "Nautobot Object"


class Nautobot(Bridge):

    """
    Service bridge for nautobot data retrieval
    """

    url_prefix = ""
    results_key = "results"

    class Meta:
        service = "nautobot"
        ref_tag = "base"
        data_object_cls = NautobotObject

    def __init__(self, key=None, org=None, **kwargs):
        if not key:
            key = DEFAULT_NAUTOBOT_TOKEN

        kwargs.setdefault("cache_duration", 10)
        kwargs.setdefault("cache", CACHE)

        super().__init__(settings.NAUTOBOT_URL, key, org, **kwargs)

    @property
    def auth_headers(self):
        return {"Authorization": f"Token {self.key}"}

    def ux_url(self, id):
        return f"{self.host}/{self.ref_tag}/{id}/?tab=main"


class DeviceTypeObject(NautobotObject):
    description = "Nautobot Device Type"


class DeviceType(Nautobot):
    class Meta(Nautobot.Meta):
        ref_tag = "dcim/device-types"
        data_object_cls = DeviceTypeObject


class DeviceObject(NautobotObject):
    description = "Nautobot Device"


class Device(Nautobot):
    class Meta(Nautobot.Meta):
        ref_tag = "dcim/devices"
        data_object_cls = DeviceObject


class InterfaceObject(NautobotObject):
    description = "Nautobot Interface"


class Interface(Nautobot):
    class Meta(Nautobot.Meta):
        ref_tag = "dcim/interfaces"
        data_object_cls = InterfaceObject


class IPAddressObject(NautobotObject):
    description = "Nautobot IP-Address"


class IPAddress(Nautobot):
    class Meta(Nautobot.Meta):
        ref_tag = "ipam/ip-addresses"
        data_object_cls = IPAddressObject


class SiteObject(NautobotObject):
    description = "Nautobot Site"


class Site(Nautobot):
    class Meta(Nautobot.Meta):
        ref_tag = "dcim/sites"
        data_object_cls = SiteObject


class CustomFieldObject(NautobotObject):
    description = "Nautobot CustomField"


class CustomField(Nautobot):
    class Meta(Nautobot.Meta):
        ref_tag = "extras/custom-fields"
        data_object_cls = CustomFieldObject

    def sync(self, fields):
        nautobot_fields = {nbf.name: nbf for nbf in self.objects()}

        for field in fields:
            nautobot_field = nautobot_fields.get(field["name"])

            if not nautobot_field:
                self.create(field)
            else:
                self.update(nautobot_field, field)
