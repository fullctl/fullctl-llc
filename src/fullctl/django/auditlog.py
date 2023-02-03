"""
Auditlogging functionality
"""

import contextvars
import inspect
import json

from django.contrib.auth import get_user_model
from django.db.models import ForeignKey, ManyToManyField, OneToOneField
from django.http import HttpRequest
from rest_framework.request import Request

from fullctl.django.inet.util import get_client_ip
from fullctl.django.models import AuditLog, Organization

User = get_user_model()

CTX_VARS = {
    "user": contextvars.ContextVar("auditlog_user"),
    "org": contextvars.ContextVar("auditlog_org"),
    "key": contextvars.ContextVar("auditlog_key"),
    "info": contextvars.ContextVar("auditlog_info"),
    "data": contextvars.ContextVar("auditlog_data"),
    "ip_address": contextvars.ContextVar("auditlog_ip_address"),
}

SENSITIVE_KEYS = [
    "password",
    "key",
    "secret",
    "token",
]

UNWANTED_KEYS = [
    "created",
    "updated",
    "version",
    "data",
    "extra",
    "csrfmiddlewaretoken",
]

UNWANTED_FIELD_TYPES = (
    OneToOneField,
    ManyToManyField,
    ForeignKey,
)


def cleaned_value(key, value):
    for skey in SENSITIVE_KEYS:
        if skey in key.lower():
            value = "[redacted]"
            break

    if isinstance(value, dict):
        cleaned_dict = {}
        for _key, _value in value.items():
            cleaned_dict[_key] = cleaned_value(_key, _value)
        return cleaned_dict

    return value


def model_tag(model):
    """
    Return the model identifier tag used for auditlog actions

    Will prefer a handlerf tag if it exists, otherwise a lowercase
    version of the model name will be returned.
    """

    try:
        return model.HandleRef.tag
    except AttributeError:
        return model.__name__.lower()


def get_config(model):
    """
    Returns the AuditLog meta class for the model if it
    exists.

    Will raise AttributeError if it does not exist
    """

    return model.AuditLog


def get_fields(model):
    fields = []
    for field in model._meta.get_fields():
        if field.is_relation:
            continue
        if field.name in UNWANTED_KEYS:
            continue
        if not isinstance(field, UNWANTED_FIELD_TYPES):
            fields.append(field.name)

    try:
        conf = get_config(model)
    except AttributeError:
        return fields

    fields += getattr(conf, "fields", [])
    return list(set(fields))


def is_enabled(model):
    """
    Returns whether the specified model is enabled for audit
    log.

    By default all reversioned models are enabled.

    To disable a model set `enabled=False` on the AuditLog
    meta class for the model
    """

    try:
        al_config = get_config(model)
    except AttributeError:
        return True

    return getattr(al_config, "enabled", True)


class Context:

    """
    Auditlog context manager
    """

    def __init__(self):
        # context variable fields
        self.fields = {}

        # auditlog entries to be persisted in the active
        # context
        self.entries = []

    def __enter__(self):
        self._init_variable("user")
        self._init_variable("key")
        self._init_variable("org")
        self._init_variable("info", default="")
        self._init_variable("data", default={})
        self._init_variable("ip_address")
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if not exc_type:
            for entry in self.entries:
                entry.save()

        for name, field in self.fields.items():
            if field["token"]:
                field["ctxvar"].reset(field["token"])

    def _init_variable(self, name, default=None):
        ctxvar = CTX_VARS.get(name)
        self.fields[name] = {"ctxvar": ctxvar, "value": default, "token": None}
        try:
            self.fields[name].update(value=ctxvar.get())
        except LookupError:
            pass

    def set(self, name, value):
        fld = self.fields[name]
        fld["token"] = fld["ctxvar"].set(value)
        fld["value"] = value

    def append_data(self, clean=False, **kwargs):
        data = self.get("data") or {}
        for key, value in kwargs.items():
            if clean:
                value = cleaned_value(key, value)
            data[key] = value
        self.set("data", data)

    def get(self, name):
        return self.fields[name].get("value")

    def log(self, action, log_object=None, info=None, **data):
        if data:
            self.set("data", data)

        if info is not None:
            self.set("info", info)

        if not self.get("org") and log_object:
            if hasattr(log_object, "org"):
                self.set("org", log_object.org)
            elif isinstance(log_object, Organization):
                self.set("org", log_object)

        data = self.get("data") or {}

        if log_object:
            snapshot = {}
            for field in get_fields(log_object):
                snapshot[field] = "{}".format(
                    cleaned_value(field, getattr(log_object, field))
                )
            data.update(snapshot=snapshot)

        entry = AuditLog(
            user=self.get("user"),
            key=self.get("key"),
            org=self.get("org"),
            data=json.dumps(data),
            action=action,
            info=self.get("info"),
            ip_address=self.get("ip_address"),
            log_object=log_object,
        )
        self.entries.append(entry)


class auditlog:

    """
    decorator for auditlog context
    """

    def __init__(self):
        pass

    def __call__(self, fn):
        def wrapped(*args, **kwargs):
            params = inspect.getcallargs(fn, *args, **kwargs)
            request = None
            user = None
            org = None
            api_key = None

            arg_candidates = (
                list(params["args"])
                + list(params["kwargs"].values())
                + list(params.values())
            )

            for arg in arg_candidates:
                if isinstance(arg, (HttpRequest, Request)):
                    request = arg
                elif isinstance(arg, User):
                    user = arg
                elif isinstance(arg, Organization):
                    org = arg

                if user and request and org:
                    break

            if request and not user and isinstance(request.user, User):
                user = request.user

            if request and hasattr(request, "api_key"):
                api_key = f"{api_key}"[:8]

            if request and not org and hasattr(request, "org"):
                org = request.org

            with Context() as ctx:
                if user:
                    ctx.set("user", user)
                if api_key:
                    ctx.set("key", api_key)
                if org:
                    ctx.set("org", org)
                if request:
                    if hasattr(request, "data"):
                        ctx.append_data(request=request.data, clean=True)
                    ctx.set("ip_address", get_client_ip(request))
                return fn(*args, auditlog=ctx, **kwargs)

        wrapped.__name__ = fn.__name__
        return wrapped
