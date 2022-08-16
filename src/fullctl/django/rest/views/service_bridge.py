import time

from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets
from rest_framework.response import Response

from fullctl.django.models import Organization
from fullctl.django.rest.core import BadRequest
from fullctl.django.rest.decorators import grainy_endpoint


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

    @grainy_endpoint("service_bridge.system")
    def list(self, request):
        return Response({"status": "ok"})


class StatusViewSet(SystemViewSet):
    ref_tag = "status"
    checks = []

    @grainy_endpoint("service_bridge.system")
    def list(self, request):

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

    def _retrieve(self, request, pk):
        qset = self.get_queryset()
        qset, joins = self.join_relations(qset, request)

        instance = qset.get(pk=pk)
        serializer = self.serializer_class(
            instance, many=False, context={"joins": joins}
        )
        return Response(serializer.data)

    @grainy_endpoint("service_bridge")
    def list(self, request, *args, **kwargs):
        return self._list(request, *args, **kwargs)

    def _list(self, request, *args, **kwargs):
        qset = self.filter(self.get_queryset(), request)

        if not self.filtered and not self.allow_unfiltered:
            return BadRequest(_("Unfiltered listing not allowed for this endpoint"))

        qset, joins = self.join_relations(qset, request)
        serializer = self.serializer_class(qset, many=True, context={"joins": joins})
        return Response(serializer.data)

    def filter(self, qset, request):
        filters = {}

        if request.GET.get("id"):
            self._filtered = True
            qset = qset.filter(pk=request.GET.get("id"))

        for url_param, django_field in self.valid_filters:

            value = request.GET.get(url_param)

            if isinstance(django_field, Exclude):
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

    @grainy_endpoint("service_bridge")
    def create(self, request, *args, **kwargs):

        data = request.data.copy()
        org_slug = data.get("org")
        if org_slug:
            data["instance"] = Organization.objects.get(slug=org_slug).instance.id

        serializer = self.serializer_class(data=data)
        if not serializer.is_valid():
            return BadRequest(serializer.errors)

        serializer.save()
        return Response(serializer.data)

    @grainy_endpoint("service_bridge")
    def partial_update(self, request, pk, *args, **kwargs):
        instance = self.get_object()

        serializer = self.serializer_class(instance, data=request.data, partial=True)

        if not serializer.is_valid():
            return BadRequest(serializer.errors)

        serializer.save()
        return Response(serializer.data)

    @grainy_endpoint("service_bridge")
    def destroy(self, request, pk, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        response = Response(serializer.data)

        instance.delete()

        return response
