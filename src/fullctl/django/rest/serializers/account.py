from django.conf import settings
from rest_framework import serializers

import fullctl.django.models as models
import fullctl.service_bridge.aaactl as aaactl
from fullctl.django.rest.decorators import serializer_registry
from fullctl.django.rest.serializers import ModelSerializer

Serializers, register = serializer_registry()


@register
class Organization(ModelSerializer):
    selected = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    access_type = serializers.SerializerMethodField()

    class Meta:
        model = models.Organization
        fields = ["slug", "name", "selected", "personal", "access_type"]

    def get_access_type(self, obj):
        user = self.context.get("user")
        if user and not user.org_set.filter(org_id=obj.id).exists():
            return "customer"
        return "member"

    def get_selected(self, obj):
        org = self.context.get("org")
        return obj == org

    def get_name(self, obj):
        if obj.personal:
            return "Personal"
        return obj.name


@register
class ASN(serializers.Serializer):
    asn = serializers.IntegerField()
    name = serializers.SerializerMethodField()

    ref_tag = "asn"

    class Meta:
        fields = ["asn", "name"]

    def get_name(self, obj):
        if obj["pdb_net"]:
            return obj["pdb_net"].name
        return ""


@register
class ContactMessage(serializers.Serializer):

    """
    Prepares a contact message for submission to the aaactl service bridge
    for the support contact backend.
    """

    message = serializers.JSONField()
    type = serializers.ChoiceField(
        choices=["support", "feature-request", "general", "demo-request"]
    )

    ref_tag = "contact_message"

    class Meta:
        fields = ["name", "email", "message"]

    def save(self):
        message = self.validated_data["message"]
        user = self.context.get("user").social_auth.first().uid
        name = self.context.get("user").username
        email = self.context.get("user").email
        typ = self.validated_data["type"]

        # we use settings.SERVICE_TAG as the slug to get the service id
        # in aaactl

        service = aaactl.ServiceApplication().first(slug=settings.SERVICE_TAG).id

        aaactl.ContactMessage().create(
            dict(
                name=name,
                email=email,
                message=message,
                service=service,
                user=user,
                type=typ,
            )
        )
