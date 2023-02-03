from rest_framework import serializers

import fullctl.django.models as models
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
