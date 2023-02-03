from secrets import token_urlsafe

import reversion
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_grainy.decorators import grainy_model

import fullctl.django.auth as auth
from fullctl.django.models.abstract import HandleRefModel

__all__ = [
    "generate_secret",
    "Organization",
    "Instance",
    "OrganizationUser",
    "UserSettings",
]


def generate_secret():
    return token_urlsafe()


COLOR_SCHEMES = (
    ("dark", _("Dark")),
    ("light", _("Light")),
)


@reversion.register()
@grainy_model(namespace="user")
class UserSettings(HandleRefModel):
    user = models.OneToOneField(
        get_user_model(), on_delete=models.CASCADE, related_name="settings"
    )
    theme = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=_("override layout theme for this user"),
    )
    color_scheme = models.CharField(
        max_length=255,
        choices=COLOR_SCHEMES,
        default="dark",
        help_text=_("user's color scheme selection"),
    )

    class HandleRef:
        tag = "user_settings"

    class Meta:
        db_table = "fullctl_user_settings"
        verbose_name = _("User settings")
        verbose_name_plural = _("User settings")


@reversion.register()
@grainy_model(namespace="org", namespace_instance="org.{instance.permission_id}")
class Organization(HandleRefModel):

    """
    Describes an organization
    """

    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=64, unique=True)
    personal = models.BooleanField(default=False)

    # if oauth manages organizations these will describe a reference
    # to the backend that created the organization

    backend = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Authentication service that created this org"),
    )
    remote_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        unique=True,
        help_text=_(
            "If the authentication service is in control of the organizations this field will hold a reference to the id at the auth service"
        ),
    )

    permission_namespaces = [
        "management",
    ]

    class Meta:
        db_table = "fullctl_org"

    class HandleRef:
        tag = "org"

    @property
    def instance(self):
        return self.instance_set.first()

    @property
    def permission_id(self):
        if self.remote_id:
            return self.remote_id
        return self.id

    @classmethod
    def accessible(cls, user):
        """
        Returns a list of organizations that are accessible by the
        user.

        Accessible here means they either have direct read permissions
        to the organization or to an object inside the organization

        **Arguments**

        - user (`User`)

        **Returns**

        - `list`
        """

        perms = auth.permissions(user)

        # user is a member of these orgs
        if hasattr(user, "org_set"):
            related_orgs = [o.org for o in user.org_set.all()]
        else:
            related_orgs = []

        # user has permissions to these orgs (customer of)
        permissioned_orgs = []

        perms.load()
        org_namespaces = perms.pset.expand("?.?", exact=True)

        for ns in org_namespaces:
            try:
                int(ns[1])
            except (ValueError, IndexError):
                continue

            try:
                org = cls.objects.get(remote_id=ns[1])
                if org not in related_orgs:
                    permissioned_orgs.append(org)
            except cls.DoesNotExist:
                pass

        return list(set(related_orgs + permissioned_orgs))

    @classmethod
    def sync(cls, orgs, user, backend):
        synced = []
        with reversion.create_revision():
            reversion.set_user(user)
            for org_data in orgs:
                org = cls.sync_single(org_data, user, backend)
                synced.append(org)

            for org in user.org_set.exclude(org__remote_id__in=[o["id"] for o in orgs]):
                org.delete()
        return synced

    @classmethod
    def sync_single(cls, data, user, backend):
        try:
            changed = False
            org = cls.objects.get(remote_id=data["id"], backend=backend)
            if data["slug"] != org.slug:
                org.slug = data["slug"]
                changed = True
            if data["name"] != org.name:
                org.name = data["name"]
                changed = True
            if data["personal"] != org.personal:
                org.personal = data["personal"]
                changed = True

            if changed:
                org.save()
        except cls.DoesNotExist:
            org = cls.objects.create(
                remote_id=data["id"],
                backend=backend,
                name=data["name"],
                slug=data["slug"],
                personal=data["personal"],
            )

        is_default = data.get("is_default", False)

        if not user.org_set.filter(org=org).exists():
            OrganizationUser.objects.create(org=org, user=user, is_default=is_default)
        else:
            user.org_set.filter(org=org).update(is_default=is_default)

        return org

    @property
    def tag(self):
        return self.slug

    @property
    def display_name(self):
        if self.personal:
            return _("Personal")
        return self.name

    @property
    def display_name_verbose(self):
        if self.personal:
            return _("your personal organization")
        return self.name

    def __str__(self):
        return f"{self.name} ({self.slug})"


@grainy_model(namespace="org")
class Instance(HandleRefModel):

    """
    app instance, one per org per app

    Needs to specify an `org` ForeignKey pointing to
    Organization
    """

    org = models.ForeignKey(
        Organization, help_text=_("owned by org"), on_delete=models.CASCADE
    )
    secret = models.CharField(max_length=255, default=generate_secret)
    app_id = "fullctl"

    class Meta:
        db_table = "fullctl_instance"

    class HandleRef:
        tag = "instance"

    @classmethod
    def get_or_create(cls, org):
        """
        Returns an organization's instance

        Will create a new instance if it does not exist
        """

        try:
            instance = cls.objects.get(org=org)
        except cls.DoesNotExist:
            instance = cls.objects.create(org=org, status="ok")
        return instance

    def __str__(self):
        return f"{self.org} ({self.id})"


@reversion.register()
@grainy_model(namespace="org")
class OrganizationUser(HandleRefModel):

    """
    Describes a user -> organization relationship
    """

    org = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="user_set"
    )
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="org_set"
    )

    is_default = models.BooleanField(default=False)

    class HandleRef:
        tag = "org_user"

    class Meta:
        db_table = "fullctl_org_user"
        verbose_name = _("Organization User")
        verbose_name_plural = _("Organization Users")

    def __str__(self):
        return f"{self.user.username} <{self.user.email}>"
