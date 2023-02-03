from rest_framework import serializers

from fullctl.django.rest.decorators import serializer_registry

Serializers, register = serializer_registry()


@register
class Usage(serializers.Serializer):
    name = serializers.CharField()
    units = serializers.FloatField()
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()

    ref_tag = "usage"

    class Meta:
        fields = ["name", "units", "start", "end"]
