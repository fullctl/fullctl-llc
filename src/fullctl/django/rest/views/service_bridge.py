import time

from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets
from rest_framework.response import Response

from fullctl.django.models import Instance, Organization
from fullctl.django.rest.core import BadRequest
from fullctl.django.rest.decorators import grainy_endpoint
from fullctl.django.rest.serializers.service_bridge import (
    HeartbeatSerializer,
    StatusSerializer,
)


class MethodFilter:
    def __init__(self, name):
        self.name = name


class Exclude:
    def __init__(self, filters):
        self.filters = filters


class SystemViewSet(viewsets.GenericViewSet):
    path_prefix = "/system"
    allowed_http_methods = ["GET"]


class HeartbeatViewSet(SystemViewSet):
    ref_tag = "heartbeat"
    serializer_class = HeartbeatSerializer

    @grainy_endpoint("service_bridge.system")
    def list(self, request):
        """
        Service heart-beat, check if the service is alive and responding
        """

        return Response({"status": "ok"})


class StatusViewSet(SystemViewSet):
    ref_tag = "status"
    serializer_class = StatusSerializer
    checks = []

    @grainy_endpoint("service_bridge.system")
    def list(self, request):
        """
        Returns service bridge status for all the service bridges
        in use
        """
        results = {}

        for check in self.checks:
            fn = getattr(self, f"check_{check}")
            t_start = time.time()
            try:
                results[check] = {"status": fn(request), "time": time.time() - t_start}
            except Exception as e:
                results[check] = {
                    "status": "failure",
                    "details": str(e),
                    "time": time.time() - t_start,
                }

        return Response(results)

    def check_bridge_peerctl(self, request):
        import fullctl.service_bridge.peerctl as peerctl

        return peerctl.Peerctl(cache_duration=1).heartbeat()

    def check_bridge_aaactl(self, request):
        import fullctl.service_bridge.aaactl as aaactl

        return aaactl.Aaactl(cache_duration=1).heartbeat()

    def check_bridge_pdbctl(self, request):
        import fullctl.service_bridge.pdbctl as pdbctl

        return pdbctl.Pdbctl(cache_duration=1).heartbeat()

    def check_bridge_ixctl(self, request):
        import fullctl.service_bridge.ixctl as ixctl

        return ixctl.Ixctl(cache_duration=1).heartbeat()

    def check_bridge_devicectl(self, request):
        import fullctl.service_bridge.devicectl as devicectl

        return devicectl.Ixctl(cache_duration=1).heartbeat()


class DataViewSet(viewsets.ModelViewSet):
    valid_filters = []
    join_xl = {}
    autocomplete = None
    allow_unfiltered = False
    allowed_http_methods = ["GET"]
    path_prefix = "/data"

    @property
    def filtered(self):
        return getattr(self, "_filtered", False)

    @grainy_endpoint("service_bridge")
    def retrieve(self, request, pk):
        return self._retrieve(request, pk)

    def serializer_context(self, request, context):
        return context

    def _retrieve(self, request, pk):
        qset = self.get_queryset()
        qset, joins = self.join_relations(qset, request)

        context = self.serializer_context(request, {"joins": joins})

        instance = qset.get(pk=pk)
        serializer = self.serializer_class(instance, many=False, context=context)
        return Response(serializer.data)

    @grainy_endpoint("service_bridge")
    def list(self, request, *args, **kwargs):
        return self._list(request, *args, **kwargs)

    def _list(self, request, *args, **kwargs):
        qset = self.filter(self.get_queryset(), request)

        if not self.filtered and not self.allow_unfiltered:
            return BadRequest(_("Unfiltered listing not allowed for this endpoint"))

        qset, joins = self.join_relations(qset, request)

        # set to a positive number to limit the number of results returned from
        # list, helps with dealing with timeouts
        limit = request.GET.get("limit", "")
        limit = int(limit) if limit.isdigit() else 0
        if limit > 0:
            qset = qset[:limit]

        context = self.serializer_context(request, {"joins": joins})

        serializer = self.serializer_class(qset, many=True, context=context)
        return Response(serializer.data)

    def filter(self, qset, request):
        filters = {}

        if request.GET.get("id"):
            self._filtered = True
            qset = qset.filter(pk=request.GET.get("id"))

        for url_param, django_field in self.valid_filters:
            value = request.GET.get(url_param)

            if value is not None and isinstance(django_field, Exclude):
                if isinstance(django_field.filters, tuple):
                    qset = qset.exclude(*django_field.filters)
                else:
                    qset = qset.exclude(django_field.filters)

            elif value is not None and isinstance(django_field, MethodFilter):
                qset = getattr(self, f"filter_{django_field.name}")(qset, value)
                self._filtered = True
            elif value is not None:
                if django_field.endswith("__in"):
                    value = value.split(",")

                self._filtered = True
                filters[django_field] = value

        return qset.filter(**filters)

    def join_relations(self, qset, request):
        join = request.GET.get("join")
        if not join:
            return qset, []

        join = join.split(",")

        for key in join:
            field = self.join_xl.get(key, (key,))
            qset = qset.select_related(*field)

        return qset, join

    def prepare_write_data(self, request):
        data = request.data.copy()
        org_slug = data.get("org")
        if org_slug:
            org = Organization.objects.get(slug=org_slug)
            data["instance"] = Instance.get_or_create(org).id

        return data

    @grainy_endpoint("service_bridge")
    def create(self, request, *args, **kwargs):
        return self._create(request, *args, **kwargs)

    def _create(self, request, *args, **kwargs):
        data = self.prepare_write_data(request)

        serializer = self.serializer_class(data=data)
        if not serializer.is_valid():
            return BadRequest(serializer.errors)

        obj = serializer.save()

        if hasattr(self, "after_create"):
            self.after_create(obj, data)

        return Response(serializer.data)

    @grainy_endpoint("service_bridge")
    def partial_update(self, request, pk, *args, **kwargs):
        data = self.prepare_write_data(request)
        instance = self.get_object()

        serializer = self.serializer_class(instance, data=data, partial=True)

        if not serializer.is_valid():
            return BadRequest(serializer.errors)

        serializer.save()

        if hasattr(self, "after_update"):
            self.after_update(instance, data)

        return Response(serializer.data)

    @grainy_endpoint("service_bridge")
    def destroy(self, request, pk, *args, **kwargs):
        self._destroy(request, pk, *args, **kwargs)

    def _destroy(self, request, pk, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        response = Response(serializer.data)

        instance.delete()

        return response
