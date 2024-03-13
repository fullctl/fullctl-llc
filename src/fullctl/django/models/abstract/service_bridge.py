from django.db import models

from fullctl.django.context import service_bridge_sync
from fullctl.django.models.abstract import HandleRefModel
from fullctl.django.models.concrete.service_bridge import ServiceBridgeAction
from fullctl.utils import rgetattr

__all__ = [
    "ServiceBridgeReferenceModel",
]


class ServiceBridgeReferenceModel(HandleRefModel):

    """
    Enables a model to have a main reference at another service
    supported by the fullctl service bridge

    Model can also have multiple additional service bridge actions
    to facilitate the pushing to remote references as well as pulling
    in additional data from secondary references.

    Should define a `ServiceBridge` Meta class with `map_{service_name}` property
    for mapping reference field names to fullctl field_names
    """

    reference_is_sot = models.BooleanField(default=True)

    class Meta:
        abstract = True

    @property
    def reference_source(self):
        """
        Returns the service name for the reference
        """
        if not self.reference or not self.reference.bridge:
            return None
        return f"{self.reference.bridge().Meta.service}"

    @property
    def reference_ux_url(self):
        """
        Returns the UX management url for the reference (if available)
        """
        if not self.reference:
            return None
        return self.reference.ux_url

    @property
    def reference_api_url(self):
        """
        Returns the API url for the reference
        """
        if not self.reference:
            return None

        return self.reference.api_url

    @property
    def fullctl_id(self):
        return self.id

    @property
    def sot(self):
        """
        Returns the source of truth object, which is either `self` or if `reference_is_sot` is `True`
        , the reference object
        """
        if self.reference_is_sot:
            return self.reference.object
        return self

    @property
    def service_bridge_actions(self):
        """
        Returns a `list` of ServiceBridgeAction instances for this model
        """
        if not hasattr(self, "_service_bridge_actions"):
            qset = ServiceBridgeAction.objects.filter(
                target__iexact=f"{self._meta.app_label}.{self._meta.model_name}"
            )
            self._service_bridge_actions = list(qset)
        return self._service_bridge_actions

    @classmethod
    def from_db(cls, *args, **kwargs):
        # When the `service_bridge_sync` context is active for pulling data
        # we want to substitute any values read from the databse with the values
        # that exist on the source of truth.
        instance = super().from_db(*args, **kwargs)
        with service_bridge_sync() as sync:
            sync.pull(instance)

        return instance

    def refresh_from_db(self, *args, **kwargs):
        # When the `service_bridge_sync` context is active for pulling data
        # we want to substitute any values read from the databse with the values
        # that exist on the source of truth.

        r = super().refresh_from_db(*args, **kwargs)

        with service_bridge_sync() as sync:
            sync.pull(self)

        return r

    def reverse_field_map(self, service_name=None):
        """
        Returns the field mapping from fullctl to reference fields
        as a dict

        Fullctl field names will be keys, reference field names will be the values
        """
        return {[(v, k) for k, v in self.field_map(service_name).items()]}

    def field_map(self, service_name=None):
        """
        Returns the field mapping from reference to fullctl fields
        as a dict

        Reference field names will be the keys, fullctl field names will be the values
        """
        if not service_name:
            service_name = self.reference.bridge().Meta.service
        return getattr(self.ServiceBridge, f"map_{service_name}")

    def sync_from_reference(self, ref_obj=None, if_sot=False, save=False):
        """
        Updates the instance from the reference using the field map (only fields
        in the field map will be updated) specified in the ServiceBridge meta
        class

        Arguments:

        - ref_obj: Service bridge entity - if not specified will use self.reference.object
        - if_sot(`bool`): only sync if `reference_is_sot` is `True`
        - save(`bool`): if changes are detected during sync, save them locally
        """

        if if_sot and not self.reference_is_sot:
            return

        if ref_obj == self:
            return

        if self.reference and not ref_obj:
            ref_obj = self.reference.object

        changed = False
        if ref_obj:
            for dest_field, src_field in self.field_map().items():
                dest_value = rgetattr(ref_obj, dest_field)
                src_value = getattr(self, src_field)
                try:
                    if dest_value == type(dest_value)(src_value):
                        continue
                except (ValueError, TypeError):
                    pass

                changed = True
                print(f"{src_field} changed from {src_value} to {dest_value}")
                setattr(self, src_field, dest_value)

        # print("sync from reference", self, changed)

        if changed and save:
            self.save()

        return changed

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # if the service_bridge_sync context is actuve for pushing
        # push updates to references

        with service_bridge_sync() as sync:
            sync.push(self)

    def push(self):
        """
        Performs push actions
        """

        actions = self.service_bridge_actions
        for action in actions:
            if action.action == "push":
                action.run_as_task(self)

    def pull(self):
        """
        Perform pull actions
        """
        actions = self.service_bridge_actions
        for action in actions:
            if action.action == "pull":
                action.run(self)

    def finalize_service_bridge_data(self, service_name, data):
        """
        Override to make final adjustments to the data generated
        through `service_bridge_data`.

        This function is called automatically by `service_bridge_data`
        """
        pass

    def service_bridge_data(self, service_name, field_map=None):
        """
        Returns a dict of fields and values according to the field map

        If no field map is providied, the default field map specified in the
        `ServiceBridge` Meta class will be used

        Arguments:

        - service_name (`str`): name of the service (e.g, pdbctl, nautbot etc.)

        - field_map (`dict`): if specified this field map will be used, should
          be a dict of reference field names mapped to fullctl field names
        """

        if not field_map:
            field_map = self.field_map(service_name)

        data = {}

        ref = self.sot

        with service_bridge_sync() as sync:
            sync.pull(self)

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

        self.finalize_service_bridge_data(service_name, data)

        return data
