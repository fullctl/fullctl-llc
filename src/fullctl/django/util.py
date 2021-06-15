from django.conf import settings

if "django_peeringdb" in settings.INSTALLED_APPS:
    import django_peeringdb.models.concrete as pdb_models
else:
    pdb_models = None


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
