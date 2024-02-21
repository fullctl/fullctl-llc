from rest_framework import serializers

import tests.django_tests.testapp.models as testapp_models
from fullctl.django.rest.serializers import SlugSerializerMixin


class TestSerializer(SlugSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = testapp_models.ModelWithSlug
        fields = ["slug"]


def test_SlugSerializerMixin():
    serializer = TestSerializer(data={"slug": "test"})
    assert serializer.is_valid() is True

    serializer = TestSerializer(data={"slug": "123"})
    assert serializer.is_valid() is False
    assert serializer.errors == {"slug": ["Slugs cannot be numeric"]}
