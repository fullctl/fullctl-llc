"""
Context manager for a service bridge context owned by a specific organization
"""
import dataclasses
from contextvars import ContextVar
from importlib import import_module

from .aaactl import ServiceApplication


@dataclasses.dataclass
class ServiceBridgeContextState:
    org_slug: str = None
    services: list = None
    org: object = None

    def load(self):
        self.services = []
        for svc in ServiceApplication().objects(group="fullctl", org=self.org_slug):
            self.services.append(svc)

    def get_service(self, *service_tags):
        for svc in self.services:
            if svc.slug in service_tags:
                return svc

        return None

    def get_service_config(self, service_tag: str, cfg_name: str, default=None):

        svc = self.get_service(service_tag)
        if svc:
            cfg = svc.config
            return getattr(cfg, cfg_name, default)
        return None

    def get_best_bridge_cls(self, *paths):
        """
        Returns a service bridge instance from a module path
        according to the first service found in the context

        paths = [
            "fullctl.service_bridge.nautobot.Device",
            "fullctl.service_bridge.netbox.Device",
        ]

        would call get_service('nautobot') and if it exists

        load and return an instance of the Device bridge using import_module
        """

        bridge_classes = []

        for path in paths:
            parts = path.split(".")
            service_tag = parts[2]
            svc = self.get_service(service_tag)
            if svc:
                bridge = getattr(import_module(".".join(parts[:-1])), parts[-1])
                if svc.federated:
                    # federated services that are a match
                    # can be returned immediately as that is the
                    # service that should be used
                    return bridge
                else:
                    # otherwise collect candidates, then return the first match
                    bridge_classes.append(bridge)

        if bridge_classes:
            return bridge_classes[0]

        return None


service_bridge_context = ContextVar(
    "service_bridge_context", default=ServiceBridgeContextState()
)


class ServiceBridgeContext:
    """
    Context manager for a service bridge context owned by a specific organization
    """

    def __init__(self, organization):
        self.state = ServiceBridgeContextState(
            org_slug=organization.slug if organization else None, org=organization
        )
        self.state.load()

    def __enter__(self):
        self.token = service_bridge_context.set(self.state)
        return self.state

    def __exit__(self, *exc):
        service_bridge_context.reset(self.token)
        return False
