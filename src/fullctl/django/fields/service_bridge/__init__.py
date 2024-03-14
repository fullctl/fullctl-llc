from logging import getLogger

from django.db.models import CharField, PositiveIntegerField

from fullctl.django.fields import CastOnAssignDescriptor
from fullctl.service_bridge.context import service_bridge_context

log = getLogger("django")


class ReferencedObject:
    @property
    def object(self):
        if not hasattr(self, "_object"):
            self._object = self.load()
        return self._object

    @property
    def ux_url(self):
        if not self.bridge:
            return None

        return self.bridge().ux_url(self.id)

    @property
    def api_url(self):
        if not self.bridge:
            return None

        return self.bridge().api_url(self.id)

    def __init__(self, bridge, id, remote_lookup="id", services=None):
        self.bridge = bridge
        self.remote_lookup = remote_lookup
        self.id = id
        self.source = None
        self.services = services

    def __repr__(self):
        return f"{self.bridge.__name__} {self.id}"

    def __str__(self):
        return f"{self.id}"

    def __int__(self):
        return self.id

    def __lt__(self, b):
        return int(self) < int(b)

    def __gt__(self, b):
        return int(self) > int(b)

    def __le__(self, b):
        return int(self) <= int(b)

    def __ge__(self, b):
        return int(self) >= int(b)

    def __len__(self):
        return len(str(self))

    def load(self):
        if not self.bridge:
            return None
        kwargs = {self.remote_lookup: self.id}
        bridge = self.bridge()
        self.source = f"{bridge.ref_tag}.{self.id}@{bridge.host}"
        return bridge.first(**kwargs)


class ReferencedObjectFieldMixin:

    """
    References an object on another fullctl service via the
    service bridge
    """

    base_type = int

    def __init__(
        self,
        bridge=None,
        remote_lookup="id",
        bridge_type=None,
        services=None,
        *args,
        **kwargs,
    ):
        if bridge and bridge_type:
            raise AttributeError("Cannot specify both bridge and bridge_type")

        if not services:
            services = []

        def get_bridge():

            if bridge:
                return bridge()

            ctx = service_bridge_context.get()
            cls = ctx.get_best_bridge_cls(*services)
            return cls()

        self.bridge_type = bridge_type
        self.services = services
        self.bridge_cls = bridge
        self.bridge = get_bridge
        self.remote_lookup = remote_lookup

        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()

        if self.bridge_type:
            kwargs["bridge_type"] = self.bridge_type
        else:
            kwargs["bridge"] = self.bridge_cls

        kwargs["services"] = self.services

        if self.remote_lookup != "id":
            kwargs["remote_lookup"] = self.remote_lookup

        return (name, path, args, kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None

        return ReferencedObject(self.bridge, value, self.remote_lookup, self.services)

    def to_python(self, value):
        if value is None:
            return None

        if isinstance(value, ReferencedObject):
            return value

        return ReferencedObject(self.bridge, value, self.remote_lookup, self.services)

    def get_prep_value(self, value):
        if value is None:
            return None
        if isinstance(value, self.base_type):
            return value
        return value.id

    def contribute_to_class(self, cls, name):
        super().contribute_to_class(cls, name)
        setattr(cls, name, CastOnAssignDescriptor(self))


class ReferencedObjectField(ReferencedObjectFieldMixin, PositiveIntegerField):
    """
    References an object on another fullctl service via the
    service bridge using a positive integer
    """

    pass


class ReferencedObjectCharField(ReferencedObjectFieldMixin, CharField):

    """
    References an object on another fullctl service via the
    service bridge using a char field
    """

    base_type = str
