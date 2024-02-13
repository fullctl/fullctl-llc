# import password input
import getpass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import CommandError

from fullctl.django.management.commands.base import CommandInterface
from fullctl.django.models.concrete.account import Organization, OrganizationUser


class Command(CommandInterface):

    """
    if `USE_LOCAL_PERMISSIONS` is set to True, this command will
    guide the user through setting up a local organization and
    the necessary permissions to use the service.
    """

    always_commit = True

    def run(self, *args, **kwargs):
        if not getattr(settings, "USE_LOCAL_PERMISSIONS", False):
            raise CommandError("Local permissions are not enabled")

        self.stdout.write("Setting up local permissions")
        self.stdout.write("-" * 80)
        self.stdout.write("")

        user = self.setup_user()
        self.setup_usergroup(user)
        self.setup_org(user)

        self.stdout.write(
            "Local permissions setup complete! Please proceed to login through the django-admin interface at /admin."
        )

    def setup_user(self):
        """
        if a superuser is not present, create one
        """

        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            username = input("Enter a username for the superuser: ")
            email = input("Enter an email for the superuser: ")
            password = getpass.getpass("Enter a password for the superuser: ")
            user = User.objects.create_superuser(username, email, password)
        else:
            user = User.objects.filter(is_superuser=True).first()

        return user

    def setup_usergroup(self, user):
        """
        create a usergroup for the superuser
        """

        group, created = Group.objects.get_or_create(name="admin")
        if created:
            group.user_set.add(user)
            group.save()
            group.grainy_permissions.add_permission("*.*", "crud")

        return group

    def setup_org(self, user):
        """
        create an organization for the superuser
        """

        org_name = input("Enter the name of the organization: ")

        slug = org_name.lower().replace(" ", "-")

        org = Organization.objects.filter(name=org_name).first()
        if not org:
            org = Organization.objects.create(name=org_name, slug=slug)
            org.save()

        OrganizationUser.objects.get_or_create(org=org, user=user, is_default=True)

        return org
