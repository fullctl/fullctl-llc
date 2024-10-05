from rest_framework import serializers

from fullctl.django.rest.decorators import serializer_registry

Serializers, register = serializer_registry()


class Stats(serializers.Serializer):
    seriesFetched = serializers.CharField()
    executionTimeMsec = serializers.IntegerField()


class Result(serializers.Serializer):
    metric = serializers.DictField()
    value = serializers.ListField(child=serializers.FloatField(), required=False)
    values = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField()), required=False
    )


class Data(serializers.Serializer):
    resultType = serializers.ChoiceField(choices=["vector", "matrix"])
    result = Result(many=True)


@register
class QueryResult(serializers.Serializer):
    """
    Describes the following metric data structure from VictoriaMetrics /query response schema:
    {
        "status": "success",
        "error": null,
        "errorType": null,
        "data": {
            "resultType": "matrix",
            "result": [
                {
                "metric": {
                    "metric": "bps_out"
                },
                "value": null,
                "values": [
                    [1724190274.126, 40874930.6311111],
                    [1724193874.126, 38638878.72],
                    // ...
                ]
                },
                {
                "metric": {
                    "metric": "bps_in"
                },
                "value": null,
                "values": [
                    [1724190274.126, 46203444.3377778],
                    [1724193874.126, 51252483.4133333],
                    // ...
                ]
                },
                {
                "metric": {
                    "metric": "bps_in_max"
                },
                "value": null,
                "values": [
                    [1724193874.126, 83122367.1466667],
                    [1724197474.126, 33460278.6133333],
                    [1724201074.126, 51380442.4533333],
                    // ...
                ]
                },
                {
                "metric": {
                    "metric": "bps_out_max"
                },
                "value": null,
                "values": [
                    [1724193874.126, 36787978.24],
                    [1724197474.126, 48718807.04],
                    // ...
                ]
                }
            ]
            },
            "stats": {
            "seriesFetched": "4",
            "executionTimeMsec": 23
        }
    }
    """

    status = serializers.CharField()
    error = serializers.CharField(allow_null=True, required=False)
    errorType = serializers.CharField(allow_null=True, required=False)
    data = Data(allow_null=True, required=False)
    stats = Stats(allow_null=True, required=False)

    ref_tag = "query_result"
