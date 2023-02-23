from rest_framework import serializers

from fullctl.django.rest.serializers import ModelSerializer


class Data(ModelSerializer):
    ref_tag = "meta_data"
    meta_source = None

    data = serializers.SerializerMethodField()

    class Meta:
        fields = ["id", "data"]

    def meta_data(self, obj, name, delete=True):
        data = obj.data
        val = data.get(name)

        if delete and name in data:
            data.pop(name)

        return val

    def get_data(self, obj):
        return obj.data
