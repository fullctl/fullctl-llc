from rest_framework import serializers

import fullctl.django.models as models
from fullctl.django.rest.decorators import serializer_registry
from fullctl.django.rest.serializers import ModelSerializer

Serializers, register = serializer_registry()


@register
class OrganizationUser(ModelSerializer):
    ref_tag = "org_user"

    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    you = serializers.SerializerMethodField()

    class Meta:
        model = models.OrganizationUser
        fields = ["id", "name", "email", "you"]

    def get_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

    def get_email(self, obj):
        return obj.user.email

    def get_you(self, obj):
        return obj.user == self.context.get("user")
