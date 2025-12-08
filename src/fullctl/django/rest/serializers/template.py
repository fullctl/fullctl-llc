from rest_framework import serializers


class TemplateSerializer(serializers.Serializer):
    """
    This serializer can be used to preview templates
    It needs to be instantiated with a TemplateBase
    object
    """

    body = serializers.SerializerMethodField()

    class Meta:
        fields = ["id", "name", "type", "body"]

    def get_body(self, obj):
        try:
            return obj.render()
        except Exception as exc:
            return (
                "!!! ERROR !!!\nWhen trying to render the template "
                "we encountered the following issue:\n\n{}\n\nPlease fix and try again.".format(
                    exc
                )
            )
