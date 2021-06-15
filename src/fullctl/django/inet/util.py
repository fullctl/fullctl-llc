from django.core.exceptions import ObjectDoesNotExist

from fullctl.django.inet.exceptions import PdbNotFoundError


def pdb_lookup(cls, **filters):
    try:
        return cls.objects.get(**filters)
    except ObjectDoesNotExist:
        raise PdbNotFoundError(cls.handleref.tag, filters)


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip
