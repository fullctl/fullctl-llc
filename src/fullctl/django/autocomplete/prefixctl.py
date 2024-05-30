from dal import autocomplete
from django.utils import html

import fullctl.service_bridge.prefixctl as prefixctl
from fullctl.django.models.concrete import Organization


class prefixctl_prefix_set(autocomplete.Select2QuerySetView):

    """
    Allows an org to search prefix sets by name or slug
    """

    def get_queryset(self):
        try:
            org = Organization.objects.get(slug=self.request.GET.get("org"))
        except Organization.DoesNotExist:
            return []

        # require_slug is a boolean that can be passed in the query string
        # if set to True, only prefix sets with a slug will be returned
        require_slug = self.request.GET.get("require_slug", False)

        if not self.request.perms.check(f"prefix_set.{org.permission_id}", "r"):
            return []

        if not self.q:
            return []

        qs = [o for o in prefixctl.PrefixSet().objects(org=org.slug, q=self.q)]

        if require_slug:
            # filter out any prefix sets that do not have a slug
            qs = [o for o in qs if o.slug]

        return qs

    def get_result_label(self, prefix_set: prefixctl.PrefixSet) -> dict:
        display_name = prefix_set.name
        display_name = html.escape(display_name)

        return {
            "primary": display_name,
            "secondary": prefix_set.slug,
        }

    def get_result_value(self, prefix_set: prefixctl.PrefixSet) -> str:
        return f"prefixctl::{prefix_set.slug}"
