try:
    from django.conf import settings

    DEFAULT_SERVICE_KEY = settings.SERVICE_KEY
except ImportError:
    DEFAULT_SERVICE_KEY = ""

from fullctl.service_bridge.client import Bridge, DataObject, url_join

CACHE = {}


class DeviceCtlEntity(DataObject):
    description = "DeviceCtl Object"
    source = "devicectl"


class Devicectl(Bridge):

    """
    Service bridge to devicectl for data
    retrieval
    """

    class Meta:
        service = "devicectl"
        ref_tag = "base"
        data_object_cls = DeviceCtlEntity

    def __init__(self, key=None, org=None, **kwargs):
        if not key:
            key = DEFAULT_SERVICE_KEY

        kwargs.setdefault("cache_duration", 10)
        kwargs.setdefault("cache", CACHE)

        super().__init__(settings.DEVICECTL_URL, key, org, **kwargs)
        self.url = url_join(self.url, "service-bridge/")


class Device(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "device"

    def request_dummy_device(self, org_slug, name, purpose):
        device = self.first(name=name, org_slug=org_slug)

        if device:
            return device

        device = self.create(
            {
                "name": name,
                "description": f"{purpose}",
                "org": org_slug,
                "type": "dummy",
            }
        )

        return device[0]

    def set_operational_status(
        self,
        device_id,
        status,
        error_message=None,
        event=None,
        url_current=None,
        url_reference=None,
        config_current=None,
        config_reference=None,
    ):
        """
        Updates the device's operational status

        Arguments:
            device_id {`int`) -- device id
            status (`str`) -- operational status (`ok` or `error`)

        Keyword Arguments:
            error_message (`str`) -- error message (default: {None})
            event (`str`) -- auditCtl event id (default: {None})
        """

        return self.post(
            f"data/device/{device_id}/set_operational_status",
            json={
                "status": status,
                "error_message": error_message,
                "event": event,
                "url_current": url_current,
                "url_reference": url_reference,
                "config_current": config_current,
                "config_reference": config_reference,
            },
        )

    def push_referee_report(self, device_id: int, report: str):
        """
        Pushes a referee report to the device in devicectl
        """

        print("Pushing referee report to device", device_id)

        return self.post(
            f"data/device/{device_id}/push_referee_report",
            json={
                "report": report,
            },
        )


class Facility(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "facility"


class Port(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "port"

    def request_dummy_ports(
        self, org_slug, ports, name_prefix, device_type, member_id_arg="id"
    ):
        return self.post(
            "data/port/request_dummy_ports",
            json={
                "org": org_slug,
                "name_prefix": name_prefix,
                "device_type": device_type,
                "ports": ports,
            },
        )


class PortInfo(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "port_info"


class VirtualPort(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "virtual_port"

    def traffic(self, pk, start_time=None, duration=None):
        params = {}
        if start_time:
            params["start_time"] = start_time

        if duration:
            params["duration"] = duration

        return self.get(
            f"data/virtual_port/{pk}/traffic",
            params=params,
        )


class IPAddress(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "ip"
