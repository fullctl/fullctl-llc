from django.db import models

from fullctl.django.models.abstract import HandleRefModel
from fullctl.utils import rgetattr

__all__ = [
    "ServiceBridgeReferenceModel",
]


class ServiceBridgeReferenceModel(HandleRefModel):

    reference_is_sot = models.BooleanField(default=True)

    class Meta:
        abstract = True

    @property
    def reference_source(self):
        return f"{self.reference.bridge.Meta.service}"

    @property
    def reference_ux_url(self):
        return self.reference.ux_url

    @property
    def reference_api_url(self):
        return self.reference.api_url

    @property
    def fullctl_id(self):
        return self.id

    @property
    def sot(self):
        if self.reference_is_sot:
            return self.reference.object
        return self

    def field_map(self, service_name=None):
        if not service_name:
            service_name = self.reference.bridge.Meta.service
        return getattr(self.ServiceBridge, f"map_{service_name}")

    def sync_from_reference(self, ref_obj=None):

        if ref_obj == self:
            return

        if self.reference and not ref_obj:
            ref_obj = self.reference.object

        changed = False
        if ref_obj:
            for dest_field, src_field in self.field_map().items():
                dest_value = rgetattr(ref_obj, dest_field)
                src_value = getattr(self, src_field)
                if dest_value == src_value:
                    continue

                changed = True
                setattr(self, src_field, dest_value)

        return changed

    # def save(self):
    #    if self.reference_is_sot and not getattr(self, "stop_sync_from_reference", False):
    #        self.sync_from_reference()
    #   return super().save()

    def service_bridge_data(self, service_name):

        field_map = self.field_map(service_name)

        data = {}

        ref = self.sot

        if self.sync_from_reference(ref):
            self.save()

        for dest_field, src_field in field_map.items():
            if "." in dest_field:
                current = data
                field_name = dest_field.split(".")[-1]
                for nested in dest_field.split(".")[:-1]:
                    current[nested] = {}
                    current = current[nested]
                current[field_name] = getattr(
                    ref, src_field, getattr(self, src_field, None)
                )
            else:
                data[dest_field] = getattr(
                    ref, src_field, getattr(self, src_field, None)
                )

        return data
