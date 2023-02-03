import fullctl.service_bridge.prefixctl as prefixctl_bridge
from fullctl.django.fields.service_bridge import ReferencedObjectField


class PrefixSet(ReferencedObjectField):
    def __init__(self, *args, **kwargs):
        kwargs["bridge"] = prefixctl_bridge.PrefixSet
        return super().__init__(*args, **kwargs)
