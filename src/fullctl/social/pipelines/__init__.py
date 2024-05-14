"""
def sync_organizations(backend, details, response, uid, user, *args, **kwargs):
    social = kwargs.get("social") or backend.strategy.storage.user.get_social_auth(
        backend.name, uid
    )
    if social:
        organizations = social.extra_data.get("organizations", [])
"""

from django.contrib.auth.models import Group


def roles_to_groups(backend, details, response, uid, user, *args, **kwargs):
    """
    Handles group assignment based on role(s) in organization.

    This requires the setting "SOCIAL_AUTH_FULLCTL_ASSIGN_GROUP_BY_ROLE" to be set to True.

    This also requires the setting "SOCIAL_AUTH_FULLCTL_LIMIT_ORGANIZATION" to be set to the organization slug.
    """

    social = kwargs.get("social") or backend.strategy.storage.user.get_social_auth(
        backend.name, uid
    )

    if not social:
        return

    # limit org must be set
    limit_org = backend.setting("LIMIT_ORGANIZATION")

    if not limit_org:
        return

    orgs = social.extra_data.get("organizations", [])

    if not orgs:
        return

    org = next((org for org in orgs if org["slug"] == limit_org), None)

    # if org not found, return
    if not org:
        return

    # cycle through all roles in org["roles"] which should be list[str]
    # then create Group if group with name does not exist
    # then add user to group

    roles = org.get("roles")

    if not roles:
        return

    # add user to group

    for role in roles:

        group_name = role

        group, _ = Group.objects.get_or_create(name=group_name)

        # only add user if they are not already in the group

        if group not in user.groups.all():

            group.user_set.add(user)

    # remove user from groups they are not in anymore

    for role in org.get("all_roles", []):

        group_name = role

        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            continue

        if group.name not in roles:
            group.user_set.remove(user)

    # finally check org.is_admin and toggle user.is_staff and
    # user.is_superuser accordingly

    if org.get("is_admin", False):
        user.is_staff = True
        user.is_superuser = True
    else:
        user.is_staff = False
        user.is_superuser = False

    user.save()
