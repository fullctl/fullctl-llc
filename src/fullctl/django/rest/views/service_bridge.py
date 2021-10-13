from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from fullctl.django.rest.core import BadRequest
from rest_framework import viewsets
from rest_framework.response import Response

class MethodFilter:
    def __init__(self, name):
        self.name = name


class Exclude:
    def __init__(self, filters):
        self.filters = filters


class DataViewSet(viewsets.ModelViewSet):
    valid_filters = []
    join_xl = {}
    autocomplete = None
    allow_unfiltered = False

    @property
    def filtered(self):
        return getattr(self, "_filtered", False)

    def retrieve(self, request, pk):
        qset = self.get_queryset()
        qset, joins = self.join_relations(qset, request)

        instance = qset.get(pk=pk)
        serializer = self.serializer_class(
            instance, many=False, context={"joins": joins}
        )
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
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


