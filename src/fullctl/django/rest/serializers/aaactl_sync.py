from django.contrib.auth import get_user_model
from rest_framework import serializers
from social_django.models import UserSocialAuth

import fullctl.django.models as models
from fullctl.django.rest.decorators import serializer_registry
from fullctl.django.rest.serializers import ModelSerializer

Serializers, register = serializer_registry()


@register
class User(ModelSerializer):
    ref_tag = "user"

    class Meta:
        model = get_user_model()
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "is_superuser",
            "is_staff",
        ]

    def save(self):
        if self.instance and self.instance.id:
            # for updates we can just call super
            return super().save()

        # create new user

        remote_id = self.context["remote_id"]

        user = get_user_model().objects.create_user(
            username=self.validated_data["username"],
            email=self.validated_data["email"],
            first_name=self.validated_data["first_name"],
            last_name=self.validated_data["last_name"],
            is_superuser=self.validated_data["is_superuser"],
            is_staff=self.validated_data["is_staff"],
        )

        # create social auth entry for aaactl (this is not
        # a valid auth at this point and the user will
        # be prompted to login with aaactl - this just
        # allows us to link the user to aaactl

        UserSocialAuth.objects.create(
            user=user,
            uid=remote_id,
            provider="twentyc",
        )

        return user


@register
class Organization(ModelSerializer):
    class Meta:
        model = models.Organization
        fields = ["name", "slug", "personal", "backend", "remote_id"]


@register
class OrganizationUser(serializers.Serializer):
    ref_tag = "org_user"
    user = serializers.IntegerField()
    default_org = serializers.IntegerField()
    orgs = serializers.ListField(child=serializers.IntegerField(), allow_empty=True)

    class Meta:
        fields = ["user", "orgs", "default_org"]

    def save(self):
        user = get_user_model().objects.get(
            social_auth__uid=self.validated_data["user"]
        )

        default_org = self.validated_data["default_org"]

        for remote_org_id in self.validated_data["orgs"]:
            try:
                org = models.Organization.objects.get(remote_id=remote_org_id)
            except models.Organization.DoesNotExist:
                continue

            if not user.org_set.filter(org=org).exists():
                models.OrganizationUser.objects.create(org=org, user=user)

        for org_user in user.org_set.all():
            if org_user.org.remote_id not in self.validated_data["orgs"]:
                org_user.delete()

        user.org_set.all().update(is_default=False)
        user.org_set.filter(org__remote_id=default_org).update(is_default=True)


@register
class ExpireSession(serializers.Serializer):
    """
    not implemented yet
    """

    username = serializers.CharField()

    ref_tag = "expire_session"

    class Meta:
        fields = ["username"]
