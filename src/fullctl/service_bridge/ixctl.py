try:
    from django.conf import settings

    DEFAULT_SERVICE_KEY = settings.SERVICE_KEY
except ImportError:
    DEFAULT_SERVICE_KEY = ""

import ipaddress
from typing import Union
from uuid import UUID

import structlog

import fullctl.service_bridge.auditctl as auditctl
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

    def set_route_server_md5(self, asn, md5, member_ip, router_ip, source):
        data = {"md5": md5, "asn": asn, "source": source}

        member_ip = ipaddress.ip_interface(member_ip).ip
        router_ip = ipaddress.ip_interface(router_ip).ip

        self.put(f"data/member/sync/{asn}/{member_ip}/{router_ip}/md5", data=data)

    def set_ports_status(self, status: str, member_id: int, member_port: int):
        return self.patch(
            f"data/member/sync/{member_id}/{member_port}/status",
            data={"status": str(status)},
        )

    def traffic(
        self,
        pk: int,
        start_time: str | int = None,
        duration: int = None,
        step: int = None,
    ):
        params = {}
        if start_time:
            params["start_time"] = start_time

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
    ):
        """
        Updates the ix members event reference

        Arguments:
            asn (`str`, `int`) -- the asn of the ix member
            address (`str`) -- the ip address of the ix member, can be either ipv4 or ipv6
            routeserver_router_id (`str`) -- router id of the routeserver i.e. 127.0.0.1
            event_reference (`str`) -- reference to the event id
        """
        return self.put(
            f"data/member/set-event-reference/{asn}/",
            json={
                "event": str(event_reference),
                "address": address,
                "routeserver_router_id": routeserver_router_id,
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

    def set_event_reference(self, router_id: str, event_reference: Union[UUID, str]):
        """
        Updates the router server's event reference

        Arguments:
            router_id (`str`) -- router id i.e. 127.0.0.1
            event_reference (`str`) -- reference to the event id
        """
        return self.put(
            f"data/routeserver/set-event-reference/{router_id}/",
            json={"event": str(event_reference)},
        )


class RouteserverMemberObject(IxctlEntity):
    description = "Ixctl Route Server Member"
    relationships = {
        "rs": {"bridge": Routeserver, "filter": ("id", "routeserver")},
        "member": {"bridge": InternetExchangeMember, "filter": ("id", "ix_member")},
        "_event": {"bridge": auditctl.Event, "filter": ("id", "event")},
    }


class RouteserverMember(Ixctl):
    class Meta(Ixctl.Meta):
        ref_tag = "routeserver_member"
        data_object_cls = RouteserverMemberObject
