from django.http import JsonResponse

from fullctl.django.rest.api_schema import SchemaGenerator


def api_schema(request):
    return JsonResponse(SchemaGenerator(title="fullCtl API").get_schema())
