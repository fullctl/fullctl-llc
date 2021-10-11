import json
import os
import time
import urllib.parse

import requests


class ServiceBridgeError(IOError):
    def __init__(self, bridge, status, data=None):
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


# Location of test data
TEST_DATA_PATH = "."


class Bridge:

    # set to > 0 if you want the bridge to cache GET
    # responses for the specified duration (seconds)
    cache_duration = 0

    class Meta:
        service = "base"

    @property
    def auth_headers(self):
        return {"Authorization": f"token {self.key}"}

    def __init__(self, host, key, org_slug, **kwargs):
        self.url = f"{host}/api"
        self.org = org_slug
        self.key = key
        self.cache = kwargs.get("cache", None)
        self.cache_duration = kwargs.get("cache_duration", 5)

    def _data(self, response):
        status = response.status_code
        if status == 200:
            return response.json().get("data")
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
            return json.load(fh)["data"]

    def get(self, endpoint, **kwargs):
        url = f"{self.url}/{endpoint}"

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
        url = f"{self.url}/{endpoint}"
        return self._data(requests.post(url, **self._requests_kwargs(**kwargs)))

    def put(self, endpoint, **kwargs):
        url = f"{self.url}/{endpoint}"
        return self._data(requests.put(url, **self._requests_kwargs(**kwargs)))

    def delete(self, endpoint, **kwargs):
        url = f"{self.url}/{endpoint}"
        return self._data(requests.delete(url, **self._requests_kwargs(**kwargs)))


class AaaCtl(Bridge):

    """
    Service bridge to aaactl

    TODO: this should probably live in the aaactl repo?
          But, do we really want to install aaactl as a package
          for each fullctl service?
    """

    def requires_billing(self, product_name):

        sub = self.require_subscription(product_name)

        if not sub:
            return False

        if not sub["pay"]:
            for item in sub.get("items"):
                if item["name"].lower() == product_name and item["cost"] > 0:
                    return True

        return False

    def require_subscription(self, product_name):
        data = self.get(f"billing/org/{self.org}/services/")

        for row in data:
            for item in row.get("items"):
                if item["name"].lower() == product_name:
                    return row

        payload = {"product": product_name}
        try:
            data = self.post(f"billing/org/{self.org}/subscribe/", data=payload)
        except ServiceBridgeError as exc:
            if exc.has_error("product", "unknown"):
                return {}
            else:
                raise
        return data[0]
