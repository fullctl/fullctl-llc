from django.db import models
from fullctl.django.models.abstract import HandleRefModel
from fullctl.utils import rgetattr

__all__ = [
    "ServiceBridgeReferenceModel",
]


class ServiceBridgeReferenceModel(HandleRefModel):

    reference_is_sot = models.BooleanField(default=True)

    class ServiceBridge:
        fields = {}

    class Meta:
        abstract = True


    def sync_from_reference(self):
        if self.reference_is_sot:
            ref_obj = self.reference.object

            for src_field, dest_field in self.ServiceBridge.fields.items():
                dest_value = rgetattr(ref_obj, dest_field)
                setattr(self, src_field, dest_value)


    def save(self):
        self.sync_from_reference()
        return super().save()
