from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.utils.safestring import mark_safe

from fullctl.django.context import current_request

register = template.Library()


@register.filter
def can_read(request, namespace):
    namespace = namespace.format(org=request.org)
    return request.perms.check(namespace, "r")


@register.filter
def can_create(request, namespace):
    namespace = namespace.format(org=request.org)
    return request.perms.check(namespace, "c")


@register.filter
def can_update(request, namespace):
    namespace = namespace.format(org=request.org)
    return request.perms.check(namespace, "u")


@register.filter
def can_delete(request, namespace):
    namespace = namespace.format(org=request.org)
    return request.perms.check(namespace, "d")


@register.filter
def can_access(request, namespace):
    namespace = namespace.format(org=request.org)
    return (
        request.perms.check(namespace, "c")
        or request.perms.check(namespace, "r")
        or request.perms.check(namespace, "u")
        or request.perms.check(namespace, "d")
    )


@register.filter
def themed_path(path):
    """
    Takes a template file path and re-routes
    it to a theme if the the requesting user
    has a theme override specified through UserSettings.theme

    In the case where the theme specified by the override
    does not exist fall back to the default theme
    """

    with current_request() as request:
        default_theme = getattr(settings, "DEFAULT_THEME", None)

        # no request in context, return path as is
        if not request:
            return path

        # attempt to revtrieve theme override for requesting
        # user.
        try:
            theme = request.user.settings.theme
        except AttributeError:
            # request.user.settings is not specified, meaning
            # user currently has no settings, return path as is
            if not default_theme:
                return path
            else:
                theme = default_theme

        # v1 switches back to original theme
        if theme == "v1":
            theme = None

        if theme:
            # theme override was found

            # keep reference to original path

            orig_path = path

            # prepend theme name to path

            parts = path.split("/")
            if len(parts) == 1:
                parts.prepend(theme)
            else:
                parts.insert(1, theme)

            path = "/".join(parts)

            # finally check if the theme exists, if it does not
            # fall back to the original path

            try:
                template.loader.get_template(path)
            except template.loader.TemplateDoesNotExist:
                return orig_path

        return path


@register.filter
def include_css(path):
    """
    This will take a path to a css file and include it
    in the template.
    """

    # user django finders module to find location of file
    # in staticfiles dirs

    path = finders.find(path)

    if isinstance(path, list):
        path = path[0]

    if not path:
        raise OSError(f"File not found: {path}")

    # read file contents

    with open(path) as f:
        content = f.read()

    # return content wrapped in style tag
    return mark_safe(f"<style>{content}</style>")
