from django.conf import settings

from fullctl.django.context import current_request

if "django_peeringdb" in settings.INSTALLED_APPS:
    import django_peeringdb.models.concrete as pdb_models
else:
    pdb_models = None


def host_url():
    """
    Will see if a current request context exist and if it
    does return host url as it exists on the requests HTTP_HOST attribute.

    Otherwise settings.HOST_URL is returned
    """

    with current_request() as request:
        if request:
            return request.META.get("HTTP_ORIGIN", settings.HOST_URL)
        return settings.HOST_URL


def verified_asns(perms):
    if not pdb_models:
        raise ImportError(
            "Peeringdb module not loaded, is `django_peeringdb` in INSTALLED_APPS?"
        )

    verified_asns = []
    for verified_asn in perms.pset.expand("verified.asn.?", explicit=True, exact=True):
        asn = verified_asn.keys[-1]
        try:
            pdb_net = pdb_models.Network.objects.get(asn=asn)
        except (ValueError, pdb_models.Network.DoesNotExist):
            pdb_net = None

        verified_asns.append({"asn": asn, "pdb_net": pdb_net})

    return verified_asns
