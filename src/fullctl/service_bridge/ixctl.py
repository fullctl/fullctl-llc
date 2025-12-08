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
        IXCTL_URL = ""


import ipaddress
from typing import Union
from uuid import UUID

import structlog

import fullctl.service_bridge.pdbctl as pdbctl
from fullctl.service_bridge.client import Bridge, DataObject, url_join

logger = structlog.getLogger(__name__)

CACHE = {}


class IxctlEntity(DataObject):
    source = "ixctl"
    description = "Ixctl Object"


class Ixctl(Bridge):
    """
    Service bridge for ixctl data retrieval
    """

    class Meta:
        service = "ixctl"
        ref_tag = "base"
        data_object_cls = IxctlEntity

    def __init__(self, key=None, org=None, **kwargs):
        if not key:
            key = DEFAULT_SERVICE_KEY

        kwargs.setdefault("cache_duration", 10)
        kwargs.setdefault("cache", CACHE)

        super().__init__(settings.IXCTL_URL, key, org, **kwargs)
        self.url = url_join(self.url, "service-bridge/")


class InternetExchangeObject(IxctlEntity):
    description = "Ixctl Exchange"


class InternetExchange(Ixctl):
    class Meta(Ixctl.Meta):
        ref_tag = "ix"
        data_object_cls = InternetExchangeObject


class InternetExhangePrefixObject(IxctlEntity):
    description = "Ixctl Exchange Prefix"
    relationships = {
        "ix": {"bridge": InternetExchange, "filter": ("ix", "ix_id")},
    }


class InternetExchangePrefix(Ixctl):
    class Meta(Ixctl.Meta):
        ref_tag = "prefix"
        data_object_cls = InternetExhangePrefixObject


class InternetExchangeMemberObject(IxctlEntity):
    description = "Ixctl Exchange Member"
    relationships = {
        "net": {"bridge": pdbctl.Network, "filter": ("asn", "asn")},
        "ix": {"bridge": InternetExchange, "filter": ("ix", "ix_id")},
    }


class InternetExchangeMember(Ixctl):
    class Meta(Ixctl.Meta):
        ref_tag = "member"
        data_object_cls = InternetExchangeMemberObject

    def set_mac_address(self, asn: int, ip: str, macaddr_set: list[str], source):
        data = {"macaddr_set": macaddr_set, "source": source}

        ip = ipaddress.ip_interface(ip).ip

        self.put(f"data/member/sync/{asn}/{ip}/mac-address", data=data)

    def set_as_macro(self, asn, as_macro, source):
        data = {"as_macro": as_macro, "asn": asn, "source": source}
        self.put("data/member/sync/as-macro", data=data)

    def set_route_server_md5(
        self,
        asn: int,
        md5: str,
        ix_id: int,
        source: str,
    ) -> dict:
        """
        Sets the ASN's md5 for the routeservers at an internet exchange
        in ixctl

        Arguments:
            asn (`int`) -- the asn of the ix member
            md5 (`str`) -- the md5 of the routeserver
            ix_id (`int`) -- the id of the internet exchange
            source (`str`) -- the source of the md5
        """
        data = {"md5": md5, "asn": asn, "source": source}

        return self.put(f"data/member/sync/{asn}/{ix_id}/md5", data=data)

    def set_ports_status(self, status: str, member_id: int, member_port: int):
        return self.patch(
            f"data/member/sync/{member_id}/{member_port}/status",
            data={"status": str(status)},
        )

    def assign_port(self, member_id: int, port_id: int, size: int, quantity: int):
        """
        Assigns a devicectl physical port to an ixctl member

        Arguments:
        - member_id (`int`) -- the id of the member (as ixctl knows it)
        - port_id (`int`) -- the id of the Port (as devicectl knows it)
            !!! this is NOT the VirtualPort, but Port.
        - size (`int`) -- the size of the individual physical port
            it is assumed that all physical ports are the same size
        - quantity (`int`) -- number of physical ports (LAG)
        """

        return self.put(
            f"data/member/{member_id}/assign-port",
            data={"port": port_id, "port_size": size, "port_quantity": quantity},
        )

    def traffic(
        self,
        pk: int,
        start_time: str | int = None,
        end_time: str | int = None,
        duration: int = None,
        step: int = None,
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

        return self.get(
            f"data/member/{pk}/traffic",
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
            f"data/member/{pk}/traffic_asn_pair",
            params={
                "asn_src": asn_src,
                "asn_dst": asn_dst,
                "start_time": start_time,
                "duration": duration,
                "step": step,
            },
        )

    def set_event_reference(
        self,
        asn: Union[str, int],
        address: str,
        routeserver_router_id: str,
        event_reference: Union[UUID, str],
        org_slug: str,
    ):
        """
        Updates the ix members event reference

        Arguments:
            asn (`str`, `int`) -- the asn of the ix member
            address (`str`) -- the ip address of the ix member, can be either ipv4 or ipv6
            routeserver_router_id (`str`) -- router id of the routeserver i.e. 127.0.0.1
            event_reference (`str`) -- reference to the event id
            org_slug (`str`) -- the org slug
        """
        return self.put(
            f"data/member/set-event-reference/{asn}/",
            json={
                "event": str(event_reference),
                "address": address,
                "routeserver_router_id": routeserver_router_id,
                "org_slug": org_slug,
            },
        )

    def metric(self, pk: int):
        return self.get(
            f"data/member/{pk}/metric",
        )

    def metric_table(self, pk: int):
        return self.get(
            f"data/member/{pk}/metric_table",
        )


class RouteserverObject(IxctlEntity):
    description = "Ixctl Route Server"
    relationships = {
        "ix": {"bridge": InternetExchange, "filter": ("ix", "ix_id")},
    }


class Routeserver(Ixctl):
    class Meta(Ixctl.Meta):
        ref_tag = "routeserver"
        data_object_cls = RouteserverObject

    def set_event_reference(
        self, router_id: str, event_reference: Union[UUID, str], org_slug: str
    ):
        """
        Updates the router server's event reference

        Arguments:
            router_id (`str`) -- router id i.e. 127.0.0.1
            event_reference (`str`) -- reference to the event id
            org_slug (`str`) -- the org slug
        """
        return self.put(
            f"data/routeserver/set-event-reference/{router_id}/",
            json={
                "event": str(event_reference),
                "org_slug": org_slug,
            },
        )


class TrafficAlertConfigObject(IxctlEntity):
    description = "Ixctl Traffic Alert Config"


class TrafficAlertConfig(Ixctl):
    class Meta(Ixctl.Meta):
        ref_tag = "traffic_alert_config"
        data_object_cls = TrafficAlertConfigObject


class TrafficAlertEmailObject(IxctlEntity):
    description = "Ixctl Traffic Alert Email"


class TrafficAlertEmail(Ixctl):
    class Meta(Ixctl.Meta):
        ref_tag = "traffic_alert_email"
        data_object_cls = TrafficAlertEmailObject

    def get_traffic_alert_email(self, ix_id: int, email_type: str, member_id: int):
        """
        Get traffic alert email

        Arguments:
            ix_id (`int`) -- The internet exchange id
            email_type (`str`) -- Type of traffic alert email i.e. 'traffic_alert_ix'
            member_id (`int`) -- The member id
        """
        return self.get(f"data/traffic_alert_email/{ix_id}/{email_type}/{member_id}")
