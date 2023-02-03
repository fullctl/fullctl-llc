import datetime

from rest_framework import viewsets
from rest_framework.response import Response

import fullctl.django.models as models
from fullctl.django.rest.decorators import grainy_endpoint
from fullctl.django.rest.mixins import CachedObjectMixin, OrgQuerysetMixin
from fullctl.django.rest.route.usage import route
from fullctl.django.rest.serializers.usage import Serializers
from fullctl.django.rest.usage import REGISTERED


@route
class Usage(CachedObjectMixin, OrgQuerysetMixin, viewsets.GenericViewSet):
    serializer_class = Serializers.usage
    queryset = models.Organization.objects.all()

    ref_tag = "usage"

    @grainy_endpoint("billing.{request.org.permission_id}")
    def list(self, request, *args, **kwargs):
        """
        List organization's usage for metered apis
        """

        data = []

        # TODO: support ranges eventually
        start = datetime.datetime.now()
        end = datetime.datetime.now()

        org = request.org

        for metric_cls in REGISTERED.values():
            metric = metric_cls(org)
            data.append(
                {
                    "name": metric.Meta.name,
                    "units": metric.calc(start, end),
                    "start": start,
                    "end": end,
                }
            )

        serializer = self.serializer_class(data, many=True)

        return Response(serializer.data)
