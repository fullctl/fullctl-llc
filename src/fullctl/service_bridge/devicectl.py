from typing import Literal

try:
    from django.conf import settings

    DEFAULT_SERVICE_KEY = settings.SERVICE_KEY
except Exception:
    # Improperly configured or django not installed
    # Improperly configured will be raised elsewhere in the app, so we can
    # ignore it here
    #
    # this allows us to use the service bridge in non-django environments
    DEFAULT_SERVICE_KEY = ""

    class settings:
        DEVICECTL_URL = ""


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

        super().__init__(kwargs.get("url", settings.DEVICECTL_URL), key, org, **kwargs)
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

    def set_ports_status(self, pk, status):
        return self.patch(
            f"data/port/{pk}/status",
            json={
                "status": status,
            },
        )

    def create_device_port(self, org_slug, name, ports):
        return self.post(
            "data/port/create_device_port",
            json={
                "org": org_slug,
                "name": name,
                "ports": ports,
            },
        )[0]

    def unassign(self, pk):
        return self.post(
            f"data/port/{pk}/unassign",
        )


class PhysicalPort(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "physical_port"

    def assign(self, pk: int, port_id: int):
        return self.post(
            f"data/physical_port/{pk}/assign",
            json={
                "port": port_id,
            },
        )

    def unassign(self, pk: int, port_id: int):
        return self.post(
            f"data/physical_port/{pk}/unassign",
            json={
                "port": port_id,
            },
        )


class PortInfo(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "port_info"


class VirtualPort(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "virtual_port"

    def traffic(
        self,
        pk,
        start_time: int | str = None,
        end_time: int | str = None,
        duration: int = None,
        step: int = None,
        traffic_source: str = "vm_sflow",
    ):
        params = {}
        if start_time:
            params["start_time"] = start_time

        if end_time:
            params["end_time"] = end_time

        if duration:
            params["duration"] = duration

        if step:
            params["step"] = step

        params["traffic_source"] = traffic_source

        return self.get(
            f"data/virtual_port/{pk}/traffic",
            params=params,
        )

    def traffic_asn_pair(
        self,
        pk: int,
        asn_src: int,
        asn_dst: int,
        start_time: int,
        duration: int,
        step: int,
    ):
        return self.get(
            f"data/virtual_port/{pk}/traffic/asn/{asn_src}/{asn_dst}",
            params={
                "start_time": start_time,
                "duration": duration,
                "step": step,
            },
        )

    def traffic_asn_table(self, pk: int, start_time: int, duration: int, step: int):
        return self.get(
            f"data/virtual_port/{pk}/traffic/asn-table",
            params={
                "start_time": start_time,
                "duration": duration,
                "step": step,
            },
        )

    def metric(self, pk):
        return self.get(
            f"data/virtual_port/{pk}/metric",
        )

    def metric_table(self, pk):
        return self.get(
            f"data/virtual_port/{pk}/metric_table",
        )

    def set_ip_addresses(self, pk: int, ipaddr4: str | None, ipaddr6: str | None):
        return self.post(
            f"data/virtual_port/{pk}/set-ip-addresses",
            json={
                "ipaddr4": str(ipaddr4) if ipaddr4 else None,
                "ipaddr6": str(ipaddr6) if ipaddr6 else None,
            },
        )

    def update_name(self, virt_port_id: int, name: str, update_logical_port: bool = True):
        """
        Updates the name of a virtual port and its logical port if specified

        Arguments:

        - `virt_port_id` (`int`) -- virtual port id
        - `name` (`str`) -- new name for the virtual port
        - `update_logical_port` (`bool`) -- whether to update the logical port name as well
        """
        virt_port = self.object(virt_port_id)
        if virt_port.name != name:
            virt_port.name = name
            self.partial_update(virt_port, {"name": name})

        if update_logical_port:
            logical_port = LogicalPort().object(virt_port.logical_port)
            if logical_port.name != name:
                logical_port.name = name
                LogicalPort().partial_update(logical_port, {"name": name})

class LogicalPort(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "logical_port"


class IPAddress(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "ip"


class PhysicalPortStats(Devicectl):
    class Meta(Devicectl.Meta):
        ref_tag = "physical_port_stats"

    def get_physical_port_stats(self, physical_ports: list[int]) -> dict[int, dict]:
        physical_port_stats = (
            list(self.objects(physical_ports=physical_ports)) if physical_ports else []
        )
        return {
            physical_port_stats.physical_port: physical_port_stats.data
            for physical_port_stats in physical_port_stats
        }

    def _merge_bgp_stats(self, physical_port_stats, bgp_stats:list[dict]):
        return self.patch(
            f"data/physical_port_stats/{physical_port_stats.id}/merge-bgp-stats",
            json={
                "physical_port": physical_port_stats.physical_port,
                "bgp_stats": bgp_stats,
            },
        )



    def save_physical_port_stats(
        self,
        data: dict | list[dict],
        org_slug: str,
        physical_port: int,
        stat_type: Literal["bgp_stats", "device_metrics"],
    ):
        """
        Saves physical port stats to the database
        """
        physical_port_stats = list(self.objects(physical_port=physical_port))
        if physical_port_stats:
            # physcal port stats exist already

            if str(stat_type) == "bgp_stats":
                # bgp stats cannot just override because multiple routeservers
                # may post them independently, so we need to merge them
                # using the merge-bgp-stats endpoint
                return self._merge_bgp_stats(physical_port_stats[0], data)

            # other stats (device metrics, ..) can just override
            initial_data = physical_port_stats[0].data.json_dict.copy()
            initial_data[stat_type] = data
            return self.put(
                f"data/physical_port_stats/{physical_port_stats[0].id}",
                json={
                    "org": org_slug,
                    "physical_port": physical_port,
                    "data": initial_data,
                },
            )

        # physcal port stats do not exist yet, create new one, data can
        # just be passed as is keyed to the stat_type
        return self.create(
            data={
                "org": org_slug,
                "physical_port": physical_port,
                "data": {
                    stat_type: data,
                },
            }
        )
