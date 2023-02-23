import contextvars
from contextlib import contextmanager

# stores current request in a thread safe context aware
# manner.
_current_request = contextvars.ContextVar("current_request")

_service_bridge_sync = contextvars.ContextVar("service_bridge_sync")

_historic = contextvars.ContextVar("historic")


@contextmanager
def historic(start_dt=None, end_dt=None):
    """
    Will yield a date range
    """

    if start_dt and end_dt:
        token = _historic.set((start_dt, end_dt))
    else:
        token = None
    try:
        yield _historic.get()
    except LookupError:
        yield None
    finally:
        if token:
            _historic.reset(token)


@contextmanager
def current_request(request=None):
    """
    Will yield the current request, if there is one.

    To se the current request for the context pass it to
    the request parameter.
    """

    if request:
        token = _current_request.set(request)
    else:
        token = None
    try:
        yield _current_request.get()
    except LookupError:
        yield None
    finally:
        if token:
            _current_request.reset(token)


class ServiceBridgeSync:

    """
    Context object for service bridge sync

    Can perform push and pull actions on objects according
    to context configuration
    """

    def __init__(self, push=False, pull=False, **kwargs):
        self.enable_push = push
        self.enable_pull = pull
        self.save = kwargs.get("save", True)
        self.cache = kwargs.get("cache")

    def push(self, obj):
        if not self.enable_push:
            return
        obj.push()

    def pull(self, obj):
        if not self.enable_pull:
            return

        if self.enable_pull == "sot" and not obj.reference_is_sot:
            return

        changed = obj.sync_from_reference(if_sot=(self.enable_pull == "sot"))
        obj.pull()

        if changed and self.save:
            obj.save()


@contextmanager
def service_bridge_sync(push=False, pull=False, cache=None, save=True):
    """
    opens a service bridge sync context in which ServiceBridgeModel
    instances will automatically pull from and push to references during
    load and save operations
    """
    token = None

    try:
        yield _service_bridge_sync.get()
    except LookupError:
        mgr = ServiceBridgeSync(push=push, pull=pull, cache=cache, save=save)
        token = _service_bridge_sync.set(mgr)
        yield mgr
    finally:
        if token:
            _service_bridge_sync.reset(token)
