"""
Utilities functions and classes for fullctl unit-testing
"""

from django.contrib.auth import get_user_model
from django.core.management.color import no_style
from django.db import connection
from django.test import Client
from rest_framework.test import APIClient

from fullctl.django.auth import permissions
from fullctl.django.models.concrete import Organization, OrganizationUser


def reset_auto_fields():
    """
    Resets the primary key field on Organization instances
    """

    sequence_sql = connection.ops.sequence_reset_sql(no_style(), [Organization])
    with connection.cursor() as cursor:
        for sql in sequence_sql:
            cursor.execute(sql)


class AccountObjects:

    """
    Sets up users and orgs for testing
    """

    def __init__(self, handle):
        reset_auto_fields()

        self.user = user = get_user_model().objects.create_user(
            username=f"user_{handle}",
            email=f"{handle}@localhost",
            password="test",
            first_name=f"user_{handle}",
            last_name="last_name",
        )

        self.other_user = get_user_model().objects.create_user(
            username=f"other_user_{handle}",
            email=f"other_{handle}@localhost",
            password="test",
            first_name=f"other_user_{handle}",
            last_name="last_name",
        )

        self.orgs = Organization.sync(
            [
                {"id": 1, "name": f"ORG{handle}", "slug": handle, "personal": True},
                {
                    "id": 2,
                    "name": f"ORG{handle}-2",
                    "slug": f"{handle}-2",
                    "personal": False,
                },
            ],
            user,
            None,
        )

        # add permissions
        user.grainy_permissions.add_permission(self.orgs[0], "crud")
        user.grainy_permissions.add_permission(f"*.{self.orgs[0].id}", "crud")
        user.grainy_permissions.add_permission(self.orgs[1], "r")
        user.grainy_permissions.add_permission(f"*.{self.orgs[1].id}", "r")

        self.org = self.orgs[0]

        OrganizationUser.objects.create(org=self.org, user=self.other_user)

        self.other_org = Organization.objects.create(
            name="Other",
            slug="other",
            id=3,
        )

        self.api_client = APIClient()
        self.api_client.login(username=user.username, password="test")

        self.client = Client()
        self.client.login(username=user.username, password="test")
        self.perms = permissions(user, refresh=True)
