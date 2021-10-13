from fullctl.service_bridge.client import Bridge, DataObject

CACHE = {}

class IxctlEntity(DataObject):
    description = "Ixctl Object"



class Ixctl(Bridge):

    """
    Service bridge for ixctl data retrieval
    """

    def __init__(self, key=None, org=None, **kwargs):

        if not key:
            key = settings.SERVICE_KEY


        kwargs.setdefault("cache_duration", 5)
        kwargs.setdefault("cache", CACHE)

        super().__init__(settings.IXCTL_HOST, key, org, **kwargs)


class InternetExchange(Ixctl):
	ref_tag = "ix"


class InternetExchangeMember(Ixctl):
	ref_tag = "member"
