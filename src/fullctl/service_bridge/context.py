"""
Context manager for a service bridge context owned by a specific organization
"""
import dataclasses
from contextvars import ContextVar

from .aaactl import ServiceApplication

@dataclasses.dataclass
class ServiceBridgeContextState:
    org_slug: str = None
    services: list = None
    org: object = None

    def load(self):
        self.services = []
        for svc in ServiceApplication().objects():
            self.services.append(svc)

    def get_service(self, *service_tags):
        for svc in self.services:
            if svc.slug in service_tags:
                return svc

        return None

service_bridge_context = ContextVar("service_bridge_context", default=ServiceBridgeContextState())

class ServiceBridgeContext:
    """
    Context manager for a service bridge context owned by a specific organization
    """
    def __init__(self, organization):
        print("ServiceBridgeContext initialized with", organization)
        self.state = ServiceBridgeContextState(
            org_slug=organization.slug if organization else None,
            org=organization
        )
        self.state.load()

    def __enter__(self):
        self.token = service_bridge_context.set(self.state)
        print("Service bridge context set", self.state.org_slug)
        return self.state

    def __exit__(self, *exc):
        service_bridge_context.reset(self.token)
        return False