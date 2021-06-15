from fullctl.django.models import Organization


def sync_organizations(backend, details, response, uid, user, *args, **kwargs):
    social = kwargs.get("social") or backend.strategy.storage.user.get_social_auth(
        backend.name, uid
    )
    if social:
        organizations = social.extra_data.get("organizations", [])
        Organization.sync(organizations, user, backend.name)
