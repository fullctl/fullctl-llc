import importlib
import logging

from django.apps import apps
from django.db import models
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _

from fullctl.django.models.abstract import HandleRefModel
from fullctl.django.models.concrete.tasks import Task, TaskLimitError
from fullctl.django.tasks import register

__all__ = [
    "ServiceBridgeAction",
]

# stores action handlers
# use @service_bridge_action decorator
# to decorate a function

handlers = {}

log = logging.getLogger(__name__)


def handler_choices():
    r = []

    for handler_info in handlers.values():
        _, _id, label = handler_info
        r.append((_id, label))

    return r


class service_bridge_action:

    """
    Decorates a function to be a service bridge action handler

    The function will then become available as a choice in the action's
    `function` propertry in django-admin

    Arguments:

    - id (`str`): unique identifier for the handler
    - label (`str`): user friendly label (use gettext)
    """

    def __init__(self, _id, label):
        self.id = _id
        self.label = label

    def __call__(self, fn):
        handlers[self.id] = (fn, self.id, self.label)
        return fn


@register
class ServiceBridgeActionTask(Task):

    """
    Task handler for ServiceBridgeAction
    """

    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_service_bridge_action"

    class TaskMeta:
        limit = 1

    @property
    def generate_limit_id(self):
        return str(self.param["args"][0]) + "." + str(self.param["args"][1])

    def run(self, action_id, obj_id):
        action = ServiceBridgeAction.objects.get(id=action_id)
        obj = action.target_model.objects.get(id=obj_id)
        action.run(obj)


class ServiceBridgeAction(HandleRefModel):

    """
    Maps a service bridge class to a fullctl handle-ref model for either
    push or pull operations in a configurable fashion.
    """

    name = models.CharField(max_length=255, unique=True)
    reference = models.CharField(
        max_length=255,
        help_text=_("should be {module_path}.{class_name} of the service bridge class"),
    )
    target = models.CharField(
        max_length=255,
        help_text=_("should be {app_label}.{mode_name} of the target model"),
    )
    description = models.CharField(max_length=255, null=True, blank=True)
    action = models.CharField(
        max_length=8, choices=(("pull", _("Pull")), ("push", _("Push"))), default="pull"
    )
    function = models.CharField(
        max_length=255, choices=lazy(handler_choices, list)(), null=True, blank=True
    )
    data_map = models.JSONField(
        null=True,
        blank=True,
        help_text=_(
            "map reference fields to target fields - only fields specified here will be affected by this action. Leave empty to use the default definitions for the model, if they exist."
        ),
        default=dict,
    )

    class HandelRef:
        tag = "service_bridge_action"

    class Meta:
        db_table = "fullctl_service_bridge_action"
        verbose_name = _("Service Bridge Action")
        verbose_name_plural = _("Service Bridge Actions")

    @property
    def target_model(self):
        """
        Returns the model class for the specified target
        """
        app_label, model = self.target.split(".")
        return apps.get_model(app_label, model)

    @property
    def reference_service_name(self):
        """
        Returns the service name of the reference source (e.g., pdbctl, nautobot etc.)
        """
        service_name, _ = tuple(self.reference.split("."))
        return service_name

    @property
    def reference_client(self):
        """
        Returns a service bridge client for the reference specified in this action
        """

        if hasattr(self, "_reference_client"):
            return self._reference_client

        service_name, class_name = tuple(self.reference.split("."))

        mod = importlib.import_module(f"fullctl.service_bridge.{service_name}")
        cls = getattr(mod, class_name)

        self._reference_client = cls()
        return self._reference_client

    def __str__(self):
        return f"ServiceBridgeAction({self.name})[{self.target} {self.action} {self.reference}]"

    def reference_object(self, obj):
        """
        Attempts to load and return the reference object for this action

        Arguments:

        - obj (`ServiceBridgeModel`)
        """

        client = self.reference_client
        service_name = self.reference_service_name

        try:
            # TODO: should lookup field be a property of ServiceBridgeAction ?

            lookup_field = getattr(obj.ServiceBridge, f"lookup_{service_name}")
            return client.first(**{lookup_field: obj.id})
        except AttributeError:
            return obj.reference.object

    def run_as_task(self, obj):
        """
        Creates a task for this action and the specified ServiceBridgeModel instance

        Arguments:

        - obj (`ServiceBridgeModel`)
        """

        try:
            ServiceBridgeActionTask.create_task(self.id, obj.id)
        except TaskLimitError:
            pass

    def run(self, obj):
        """
        Runs this action for the specified ServiceBridgeModel instance
        """

        fn = getattr(self, self.action)
        fn(obj)

    def push(self, obj):
        """
        Pushes data for the specified ServiceBridgeModel instance to the reference
        using th service bridge

        Arguments:

        - obj (`ServiceBridgeModel`)
        """

        client = self.reference_client
        service_name = self.reference_service_name
        reference_object = self.reference_object(obj)

        # data = obj.service_bridge_data(service_name, self.data_map)

        if not self.function:
            # No function handler is specified, perform a data push

            if not reference_object:
                # reference object does not exist yet, create it

                client.create(obj.service_bridge_data(service_name))

            elif not self.data_map:
                # reference object exists and no custom field mapping has been provided
                # perform a PUT update using the pre-defined service bridge field map for
                # the service

                # TODO: specify method in schema?

                client.update(reference_object, obj.service_bridge_data(service_name))

            else:
                # reference object exists and custom field mapping has been provided
                # perform a PATCH update using the custom field mapping

                # TODO: specify method in schema?

                client.partial_update(
                    reference_object,
                    obj.service_bridge_data(service_name, self.data_map),
                )
        else:
            # Function handler specified, attempt to run it

            try:
                fn, _, _ = handlers[self.function]
            except KeyError:
                log.error(
                    f"Unknown service bridge action handler specified on {self}: {self.function}"
                )
                return
            fn("push", obj)

    def pull(self, obj):
        """
        Pulls data for the specified ServiceBridgeModel instance from the reference using
        the service bridge

        Arguments:

        - obj (`ServiceBridgeModel`)
        """

        if self.function:
            try:
                fn, _, _ = handlers[self.function]
            except KeyError:
                log.error(
                    f"Unknown service bridge action handler specified on {self}: {self.function}"
                )
                return
            fn("pull", obj)
