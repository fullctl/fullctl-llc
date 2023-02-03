from rest_framework import serializers


class HeartbeatSerializer(serializers.Serializer):
    status = serializers.CharField()

    class Meta:
        fields = ["status"]


class StatusSerializer(serializers.Serializer):
    pass
