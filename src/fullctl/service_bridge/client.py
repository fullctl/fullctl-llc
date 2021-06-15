import requests


class ServiceBridgeError(IOError):
    def __init__(self, bridge, status, data=None):
        super().__init__(f"Service bridge error: {bridge} [{status}]")
        self.data = data

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
    class Meta:
        service = "base"

    def __init__(self, host, key, org_slug):
        self.url = f"{host}/api"
        self.org = org_slug
        self.key = key

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

    def get(self, endpoint, **kwargs):
        url = f"{self.url}/{endpoint}?key={self.key}"
        return self._data(requests.get(url, **kwargs))

    def post(self, endpoint, **kwargs):
        url = f"{self.url}/{endpoint}?key={self.key}"
        return self._data(requests.post(url, **kwargs))


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
