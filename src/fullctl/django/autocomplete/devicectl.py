from dal import autocomplete
from django.utils import html

import fullctl.service_bridge.devicectl as devicectl
from fullctl.django.models.concrete import Organization


class devicectl_port(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        try:
            org = Organization.objects.get(slug=self.request.GET.get("org"))
        except Organization.DoesNotExist:
            return []

        if not self.request.perms.check(f"port.{org.permission_id}", "r"):
            return []

        if not self.q:
            return []

        qs = [o for o in devicectl.Port().objects(org_slug=org.slug, q=self.q)]
        return qs

    def get_result_label(self, port):
        display_name = port.display_name

        if not display_name or display_name == "-":
            display_name = "No IPs set"

        display_name = html.escape(display_name)
        virtual_port_name = html.escape(port.virtual_port_name)

        try:
            device_name = html.escape(port.device_name)
        except AttributeError:
            device_name = "No device connected"

        return {
            "primary": display_name,
            "secondary": virtual_port_name,
            "extra": device_name,
        }
