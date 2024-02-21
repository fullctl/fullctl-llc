class CachedObjectMixin:

    """
    Assures that a views get_object() call only
    queries the db once
    """

    def get_object(self):
        if getattr(self, "_obj", None) is None:
            self._obj = super().get_object()

        return self._obj


class SlugObjectMixin:

    """
    Assures that a views get_object() can do a lookup
    via either the slug or the id
    """

    slug_field = "slug"

    def get_object(self):
        """
        pk could be either slug or id
        """

        lookup_value = self.kwargs.get(self.lookup_field)
        org_tag = self.kwargs.get("org_tag")

        if not lookup_value:
            return None

        if lookup_value.isdigit():
            return self.queryset.get(instance__org__slug=org_tag, id=lookup_value)
        else:
            return self.queryset.get(instance__org__slug=org_tag, slug=lookup_value)


class OrgQuerysetMixin:
    """
    For objects with URLs that require an "org_tag", this filters
    the resulting queryset by matching the instance org to the
    provided slug.
    """

    def get_queryset(self):
        org_tag = self.kwargs["org_tag"]
        return self.queryset.filter(instance__org__slug=org_tag)


class ContainerQuerysetMixin:
    """
    For objects with URLS that require an "org_tag" as well as
    a secondary tag from a container entity,
    this filters the resulting queryset by matching the org slug and the
    container entity slug to the url tags

    Class needs to define the following class properties

    - container_url_field (`str`): the name of the url parameter identified the container
    - container_lookup_field (`str`): the database field to use for lookups
    """

    def get_queryset(self):
        org_tag = self.kwargs["org_tag"]
        container_tag = self.kwargs[self.container_url_field]
        container_lookup_field = self.container_lookup_field

        filters = {
            f"{container_lookup_field}__slug": container_tag,
            f"{container_lookup_field}__instance__org__slug": org_tag,
        }

        return self.queryset.filter(**filters)
