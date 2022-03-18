import pytest
from django.test import Client


class AccountObjects:
    def __init__(self, handle):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient

        from fullctl.django.auth import permissions
        from fullctl.django.models import Organization, OrganizationUser

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
        user.grainy_permissions.add_permission(self.orgs[1], "r")

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

        self.perms = permissions(user)


def make_account_objects(handle="test"):
    return AccountObjects(handle)


@pytest.fixture
def dj_client_anon():
    return Client()


@pytest.fixture
def dj_account_objects():
    return make_account_objects()


@pytest.fixture
def dj_account_objects_b():
    return make_account_objects("test_b")


@pytest.fixture
def dj_account_objects_c():
    return make_account_objects("test_c")
