import json
import os
import time
import urllib.parse

import requests
import requests.exceptions

from fullctl.service_bridge.data import DataObject


def trim_endpoint(endpoint):
    """
    urljoin is not guaranteed to strip trailing double slashes on
    either side of the endpoint, so we do it manually
    """
    return endpoint.strip("/")


def url_join(left, *args):
    """
    Simplified urljoin that gets of extra / at the edges
    of parts
    """

    right = []

    for parts in args:
        right.extend([trim_endpoint(part) for part in parts.split("/") if part])

    right = "/".join(right)

    if not left:
        return f"/{right}/"

    return f"{left.rstrip('/')}/{right}/"


# Location of test data
TEST_DATA_PATH = "."


class ServiceBridgeError(IOError):
    def __init__(self, bridge, status, data=None):
        if data:
            super().__init__(
                f"Service bridge error: {bridge} [{status}] - response data: {data}"
            )
        else:
            super().__init__(f"Service bridge error: {bridge} [{status}]")
        self.data = data
        self.status = status

    @property
    def errors(self):
        if not self.data:
            return {}

        return self.data["errors"]

    def has_error(self, key, text):
        errors = ";".join(self.errors.get(key, []))
        return text.lower() in errors.lower()


class AuthError(ServiceBridgeError):
    pass


class Bridge:
    # set to > 0 if you want the bridge to cache GET
    # responses for the specified duration (seconds)
    cache_duration = 0

    results_key = "data"
    url_prefix = "data"

    class Meta:
        service = "base"
        ref_tag = "base"
        data_object_cls = DataObject

    @property
    def auth_headers(self):
        return {"Authorization": f"token {self.key}"}

    @property
    def ref_tag(self):
        return self.Meta.ref_tag

    @property
    def data_object_cls(self):
        return self.Meta.data_object_cls

    def __init__(self, host, key, org_slug, **kwargs):
        self.url = url_join(host, "/api/")
        self.org = org_slug
        self.key = key
        self.host = host
        self.cache = kwargs.get("cache", None)
        self.cache_duration = kwargs.get("cache_duration", 5)

    def _data(self, response):
        status = response.status_code
        if status in [200, 201, 202, 203, 204, 205]:
            return response.json().get(self.results_key)
        elif status in [401, 403]:
            raise AuthError(self, status)
        elif status in [400]:
            raise ServiceBridgeError(self, 400, data=response.json())
        else:
            raise ServiceBridgeError(self, status)

    def _requests_kwargs(self, **kwargs):
        if kwargs.get("headers"):
            kwargs["headers"].update(self.auth_headers)
        else:
            kwargs["headers"] = self.auth_headers

        return kwargs

    def cached(self, url, now, params):
        if self.cache is None:
            return None
        data, timestamp = self.cache.get(url, {}).get(params, (None, 0))
        if now - timestamp > self.cache_duration:
            return None
        return data

    def test_data(self, path, params):
        if params:
            param_str = "/" + urllib.parse.quote(urllib.parse.urlencode(params))
        else:
            param_str = ""
        file_path = os.path.join(TEST_DATA_PATH, f"{path.rstrip('/')}{param_str}.json")
        with open(file_path) as fh:
            return json.load(fh)[self.results_key]

    def get(self, endpoint, **kwargs):
        url = url_join(self.url, endpoint)

        # if the url starts with a test:// protocol, attempt
        # to load test data from path instead.
        if url.startswith("test://"):
            return self.test_data(url.split("://")[1], kwargs.get("params"))

        now = time.time()
        params = json.dumps(kwargs.get("params"))

        cached_data = self.cached(url, now, params)
        if cached_data:
            return cached_data

        data = self._data(requests.get(url, **self._requests_kwargs(**kwargs)))

        if self.cache is not None:
            self.cache.setdefault(url, {})[params] = (data, now)

        return data

    def post(self, endpoint, **kwargs):
        url = url_join(self.url, endpoint)
        return self._data(requests.post(url, **self._requests_kwargs(**kwargs)))

    def put(self, endpoint, **kwargs):
        url = url_join(self.url, endpoint)
        return self._data(requests.put(url, **self._requests_kwargs(**kwargs)))

    def patch(self, endpoint, **kwargs):
        url = url_join(self.url, endpoint)
        return self._data(requests.patch(url, **self._requests_kwargs(**kwargs)))

    def delete(self, endpoint, **kwargs):
        url = url_join(self.url, endpoint)
        try:
            return self._data(requests.delete(url, **self._requests_kwargs(**kwargs)))
        except ServiceBridgeError as exc:
            if exc.status == 404:
                pass
            else:
                raise

    def object(self, id, raise_on_notfound=True, join=None):
        url = f"{self.url_prefix}/{self.ref_tag}/{id}"
        params = {}

        if join:
            params.update(join=join)
        data = self.get(url, params=params)
        try:
            return self.data_object_cls(ref_tag=self.ref_tag, **data[0])
        except IndexError:
            if raise_on_notfound:
                raise KeyError(f"{self.data_object_cls.description} does not exist")
            return None

    def objects(self, **kwargs):
        url = f"{self.url_prefix}/{self.ref_tag}"
        for k, v in kwargs.items():
            if isinstance(v, list):
                kwargs[k] = ",".join([str(a) for a in v])
        data = self.get(url, params=kwargs)
        for row in data:
            yield self.data_object_cls(ref_tag=self.ref_tag, **row)

    def create(self, data):
        url = f"{self.url_prefix}/{self.ref_tag}"
        data = self.post(url, json=data)
        return data

    def destroy(self, obj):
        url = f"{self.url_prefix}/{self.ref_tag}/{obj.id}"
        try:
            data = self.delete(url)
            return data
        except requests.exceptions.JSONDecodeError:
            return {}

    def update(self, obj, data):
        url = f"{self.url_prefix}/{self.ref_tag}/{obj.id}"
        data = self.put(url, json=data)
        return data

    def partial_update(self, obj, data):
        url = f"{self.url_prefix}/{self.ref_tag}/{obj.id}"
        data = self.patch(url, json=data)
        return data

    def update_if_changed(self, obj, data):
        diff = {}

        for field, value in data.items():
            if getattr(obj, field) != value:
                diff[field] = value

        if not diff:
            return

        url = f"{self.url_prefix}/{self.ref_tag}/{obj.id}"
        data = self.patch(url, data=diff)

        return data

    def first(self, **kwargs):
        for o in self.objects(**kwargs):
            return o

    def heartbeat(self):
        data = self.get("system/heartbeat")
        return data[0].get("status")

    def status(self):
        data = self.get("system/status")
        return data[0]

    def ux_url(self, id):
        return None

    def api_url(self, id):
        endpoint = f"{self.url_prefix}/{self.ref_tag}/{id}"
        url = url_join(self.url, endpoint)
        return url


class AaaCtl(Bridge):

    """
    Service bridge to aaactl

    TODO: move to service_bridge/aaactl.py
    """

    def requires_billing(self, product_name):
        subscription = self.require_subscription(product_name)

        if not subscription:
            return False

        if not subscription["payment_method"]:
            for item in subscription.get("items"):
                if item["name"].lower() == product_name and item["cost"] > 0:
                    return True

        return False

    def require_subscription(self, product_name):
        data = self.get(f"billing/org/{self.org}/services")

        for row in data:
            for item in row.get("items"):
                if item["name"].lower() == product_name:
                    return row

        payload = {"product": product_name}
        try:
            data = self.post(f"billing/org/{self.org}/subscribe", data=payload)
        except ServiceBridgeError as exc:
            if exc.has_error("product", "unknown"):
                return {}
            else:
                raise
        return data[0]
