import structlog
from django.conf import settings

import fullctl.service_bridge.auditctl as auditctl

log = structlog.get_logger(__name__)


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


class AuditCtlActionLogMixin:
    """
    This viewset mixin allows actions taken on a viewset to be logged
    to auditctl.

    Only actions that are defined in the AUDITCTL_LOG_API_ACTIONS setting
    will be logged.

    Only WRITE actions (POST, PUT, DELETE, PATCH) will be logged.

    The ref_tag is determined by the viewset's ref_tag attribute or the
    serializer's ref_tag attribute.

    The action is determined by the method name of the viewset handler.

    If the viewset has an auditctl_log_append_path method, it will be
    called to determine additional path components to append to the
    object_id. (auditctl event path)
    """

    def is_action_enabled_for_logging(self, request, ref_tag: str, action: str) -> bool:
        """
        Check if a specific action is enabled for logging
        """

        if not settings.AUDITCTL_LOG_API_ACTIONS or not ref_tag or not action:
            return False

        # discard all read methods
        if request.method.lower() not in ["post", "put", "delete", "patch"]:
            return False

        for action_ref in settings.AUDITCTL_LOG_API_ACTIONS:
            if ":" in action_ref:
                ref_tag, action_ref = action_ref.split(":")
            else:
                ref_tag, action_ref = action_ref, "*"

            if ref_tag == ref_tag and (action_ref == "*" or action_ref == action):
                return True

        return False

    def finalize_response(self, request, response, *args, **kwargs):
        """
        Logs certain api actions to the auditctl service
        """

        response = super().finalize_response(request, response, *args, **kwargs)

        if request.method.lower() not in self.http_method_names:
            return response

        if not settings.AUDITCTL_LOG_API_ACTIONS:
            return response

        try:
            handler = getattr(
                self, request.method.lower(), self.http_method_not_allowed
            )

            action = handler.__name__

            ref_tag = getattr(
                self, "ref_tag", getattr(self.serializer_class, "ref_tag", None)
            )

            if not self.is_action_enabled_for_logging(request, ref_tag, action):
                return response

            if hasattr(self, "auditctl_log_append_path"):
                append_path = self.auditctl_log_append_path(request, action, **kwargs)
            else:
                append_path = None

            api_key = getattr(request, "api_key", None)

            auditctl.Event().log_action(
                org_slug=request.org.slug,
                service=settings.SERVICE_TAG,
                ref_tag=ref_tag,
                action=action,
                id=kwargs.get(self.lookup_url_kwarg),
                payload=request.data,
                request_url=request.build_absolute_uri(),
                status_code=response.status_code,
                append_path=append_path,
                username=request.user.username if request.user else None,
                api_key=api_key[:4] + "..." + api_key[-4:] if api_key else None,
            )

        except Exception as e:
            log.error(f"Failed to log action to auditctl: {e}")

        return response
