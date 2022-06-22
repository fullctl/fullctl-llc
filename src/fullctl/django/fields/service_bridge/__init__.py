
from django.db.models import PositiveIntegerField

class ReferencedObject:


    @property
    def object(self):
        if not hasattr(self, "_object"):
            self._object = self.load()
        return self._object

    def __init__(self, bridge, id, remote_lookup="id"):
        self.bridge = bridge
        self.remote_lookup = remote_lookup
        self.id = id
        self.source = None

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

    def load(self):
        kwargs = {self.remote_lookup:self.id}
        bridge = self.bridge()
        self.source = f"{bridge.ref_tag}.{self.id}@{bridge.host}"
        return bridge.first(**kwargs)





class ReferencedObjectField(PositiveIntegerField):

    """
    References an object on another fullctl service via the
    service bridge
    """

    def __init__(self, bridge=None, remote_lookup="id", *args, **kwargs):
        self.bridge = bridge
        self.remote_lookup = remote_lookup
        super().__init__(*args, **kwargs)

    def deconstruct(self):

        name, path, args, kwargs = super().deconstruct()

        kwargs["bridge"] = self.bridge
        if self.remote_lookup != "id":
            kwargs["remote_lookup"] = self.remote_lookup

        return (name, path, args, kwargs)

    def from_db_value(self, value, expression, connection):

        if value is None:
            return None

        return ReferencedObject(self.bridge, value, self.remote_lookup)

    def to_python(self, value):

        if value is None:
            return None

        if isinstance(value, ReferencedObject):
            return value

        return ReferencedObject(self.bridge, value, self.remote_lookup)


    def get_prep_value(self, value):
        return value.id
