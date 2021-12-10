from django import template

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
