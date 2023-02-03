from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class SoftRequiredValidator:
    """
    A validator that allows us to require that at least
    one of the specified fields is set
    """

    message = _("This field is required")
    requires_context = True

    def __init__(self, fields, message=None):
        self.fields = fields
        self.message = message or self.message

    def set_context(self, serializer):
        self.instance = getattr(serializer, "instance", None)

    def __call__(self, attrs, serializer):
        missing = {
            field_name: self.message
            for field_name in self.fields
            if not attrs.get(field_name)
        }
        valid = len(self.fields) != len(missing.keys())
        if not valid:
            raise ValidationError(missing)


class ModelSerializer(serializers.ModelSerializer):
    grainy = serializers.SerializerMethodField(help_text="Grainy permission namespace")

    status = serializers.CharField(help_text="Object status", read_only=True)

    def get_grainy(self, obj):
        if hasattr(obj, "Grainy"):
            return obj.Grainy.namespace(obj)
        return None


class RequireContext:
    required_context = []

    def validate(self, data):
        data = super().validate(data)

        for key in self.required_context:
            if key not in self.context:
                raise serializers.ValidationError(_(f"Context missing: {key}"))

        return data
