from datetime import datetime

from django.conf import settings

from fullctl.django.context import current_request

if "django_peeringdb" in settings.INSTALLED_APPS:
    import django_peeringdb.models.concrete as pdb_models
else:
    pdb_models = None


DEFAULT_FULLCTL_BRANDING = {
    "name": "FullCtl",
    "html_footer": f"Copyright © 2014 - {datetime.now().year} FullCtl, LLC",
    "css": {"primary_color": "#D1FF27"},
    "dark_logo_url": None,
    "light_logo_url": None,
    "custom_org": False,
    "show_logo": True,
}


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

    verified_asns = []
    for verified_asn in perms.pset.expand("verified.asn.?", explicit=True, exact=True):
        asn = verified_asn.keys[-1]

        pdb_net = None
        if pdb_models:

            # if peeringdb is installed, we can look up the network locally
            # otherwise we will just return the asn

            try:
                pdb_net = pdb_models.Network.objects.get(asn=asn)
            except (ValueError, pdb_models.Network.DoesNotExist):
                pass

        verified_asns.append({"asn": asn, "pdb_net": pdb_net})

    return verified_asns
