from django.conf import settings

from fullctl.service_bridge.client import Bridge

CACHE = {}


class PeeringDBEntity:
    @property
    def pk(self):
        return self.id

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if isinstance(v, dict):
                setattr(self, k, PeeringDBEntity(**v))
            else:
                setattr(self, k, v)


class Pdbctl(Bridge):

    """
    Service bridge to pdbctl for peeringdb data
    retrieval
    """

    def __init__(self, key=None, org=None, **kwargs):
        if not key:
            key = settings.SERVICE_KEY

        kwargs.setdefault("cache_duration", 5)
        kwargs.setdefault("cache", CACHE)

        super().__init__(settings.PDBCTL_HOST, key, org, **kwargs)

    def model_args(self, data):
        data.pop("grainy", None)
        return data

    def object(self, id, raise_on_notfound=True, join=None):
        url = f"{self.ref_tag}/{id}/"
        params = {}
        if join:
            params.update(join=join)
        data = self.get(url, params=params)
        try:
            return PeeringDBEntity(**data[0])
        except IndexError:
            if raise_on_notfound:
                raise KeyError("PeeringDB entity does not exist")
            return None

    def objects(self, **kwargs):
        url = f"{self.ref_tag}"
        for k, v in kwargs.items():
            if isinstance(v, list):
                kwargs[k] = ",".join([str(a) for a in v])
        data = self.get(url, params=kwargs)
        for row in data:
            yield PeeringDBEntity(**row)

    def first(self, **kwargs):
        for o in self.objects(**kwargs):
            return o


class InternetExchange(Pdbctl):
    ref_tag = "ix"


class Network(Pdbctl):
    ref_tag = "net"


class NetworkIXLan(Pdbctl):
    ref_tag = "netixlan"


class NetworkContact(Pdbctl):
    ref_tag = "poc"
