import json

import requests
from django.conf import settings
from django.http import JsonResponse
from django.urls import include, path

PROXIED = {}


def proxy_api(service, host, endpoints):
    """
    proxies a fullctl service's api with it's endpoints
    exposed to the local service's api 1:1
    """

    paths = [
        proxy_api_endpoint(
            service, host, {"remote": remote, "local": local, "name": name}
        )
        for remote, local, name in endpoints
    ]

    return include(paths)


def proxy_api_endpoint(service, host, endpoint):
    def view_proxy(request, org_tag, *args, **kwargs):
        api_key = settings.SERVICE_KEY
        method = request.method.lower()
        request_fn = getattr(requests, method)

        # drf_request = Request(request, parsers=[JSONParser])
        _kwargs = {}

        if method in ["post", "put", "patch"]:
            _kwargs.update(json=json.loads(request.body))
        elif method == "get":
            _kwargs.update(params=request.GET)

        endpoint_remote = endpoint["remote"].format(org_tag=org_tag, **kwargs)

        url = f"{host}/api/{endpoint_remote}"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-User": request.user.social_auth.first().uid,
        }

        response = request_fn(url, headers=headers, **_kwargs)
        print("proxied response in", response.elapsed.total_seconds())

        json_dumps_params = {}

        if "pretty" in request.GET:
            json_dumps_params.update(indent=2)

        return JsonResponse(
            response.json(),
            status=response.status_code,
            json_dumps_params=json_dumps_params,
        )

    return path(
        endpoint["local"], view_proxy, name=f"proxies-api-{service}-{endpoint['name']}"
    )


def setup(service, patterns):
    if service in PROXIED:
        print(f"Proxied api for service {service} already setup")
        return

    PROXIED[service] = patterns


def urlpatterns(supported_services):
    urlpatterns = []

    for service, patterns in PROXIED.items():
        urlpatterns.append(path("api/", patterns))

    return urlpatterns
