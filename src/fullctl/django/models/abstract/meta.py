"""
Abstract classes to facilitate the fetching, caching and retrieving of meta data
sourced from third party sources.
"""
import json
import re
import time
from datetime import timedelta

import confu.schema
import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from fullctl.django.models.abstract import HandleRefModel

__all__ = ["Request", "Response", "Data", "NoMetaClassDefined"]


class NoMetaClassDefined(ValueError):
    pass


class DataMixin:
    def clean_data(self):
        """
        If the model has a DataSchema confu schema
        defined, the schema will be used to validate the data
        in self.data
        """

        if not hasattr(self, "DataSchema"):
            return

        for name in dir(self.DataSchema):
            if name.startswith("_"):
                continue

            data = getattr(self, name)
            schema = getattr(self.DataSchema, name)

            try:
                confu.schema.validate(schema(), data, raise_errors=True)
            except confu.schema.ValidationError as exc:
                raise ValidationError(f"Invalid meta-data in {name}: {exc}")


class Data(HandleRefModel):

    """
    Normalized object meta data
    """

    source_name = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=255, default="info")
    data = models.JSONField()
    date = models.DateTimeField(help_text="Data validity start date")

    class Meta:
        abstract = True

    class HandleRef:
        tag = "meta_data"

    class Config:
        # historic period in seconds
        period = 12 * 3600
        type = "info"

    @classmethod
    def cleanup(cls, target=None, age=None):
        return

    @classmethod
    def config(cls, config_name, default=None):
        value = getattr(cls.Config, config_name, default)

        if value is None:
            raise ValueError(f"`{cls}.Config.{config_name}` property not specified")

        return value

    def update(self, data):
        self.data = data

    def __str__(self):
        return f"{self.type}:{self.source_name}:{self.date}"


class Request(HandleRefModel):

    """
    Handles logic for requesting and rate-throttling third party meta data
    """

    source = models.CharField(max_length=255)
    type = models.CharField(max_length=255, null=True, blank=True)
    url = models.URLField()
    http_status = models.PositiveIntegerField()
    payload = models.JSONField(null=True, blank=True)
    count = models.PositiveIntegerField(default=1)

    valid_http_status = [200]

    # what to do on too many requests

    # how long to wait before retrying
    retry_429_interval = 1

    # how many times to try before giving up
    retry_429_tries = 2

    processing_error = models.CharField(
        max_length=255,
        help_text="will hold error information if the request came back as a success but reading its data resulted in an error on our end.",
        null=True,
        blank=True,
    )

    class Config:
        cache_expiry = 86400
        source_name = None

    class HandleRef:
        tag = "meta_request"

    class Meta:
        abstract = True

    @classmethod
    def prepare_request(cls, targets):
        """
        will make sure targets are always converted
        into a list object

        override this method for more complex preparation
        of request targets

        Arguments:

        - targets (`list|mixed`)

        Returns:

        - targets (`list`)
        """

        if not isinstance(targets, list):
            return [targets]
        return targets

    @classmethod
    def request(cls, targets):
        """
        Requests data for one or more targets

        This will honor both request and response cache layers
        """

        targets = cls.prepare_request(targets)
        results = {}

        for target in targets:
            results[f"{target}"] = cls.request_target(target)

        return results

    @classmethod
    def request_target(cls, target, ignore_cache=False):
        """
        Requests data for the specified target

        This will honor both request and response cache layers and will
        return the `Request` instance for it if exists and is valid.

        Arguments:

        - target: the target of the request, will be processed through `target_to_url`
          class method to convert into a requestable url.

        Keyword arguments:

        - ignore_cache (`bool`): if True both cache layers will be ignored


        Returns:

        - request (`Request`)
        """

        request = cls.get_cache(target)

        if request:
            return cls.process(
                target,
                request.url,
                request.http_status,
                request.response.data,
                cached=True,
                content=request.response.content,
            )

        return cls.send(target)

    @classmethod
    def target_to_url(cls, target):
        """
        override this to handle converting a target to a requestable url
        """

        raise NotImplementedError()

    @classmethod
    def target_to_type(cls, target):
        """
        override this to handle converting a target to a requestable url
        """
        return None

    @classmethod
    def send(cls, target):
        """
        Send request to third party api to retrieve data for target.

        In some cases it may make sense to override this in an extended class
        to implemnt more complex fetching logic.

        In this impementation a GET request is sent off using the `requests`
        module and expecting a json response.
        """

        url = cls.target_to_url(target)

        _resp = None

        tries = 0
        while not _resp or _resp.status_code == 429:
            print("seding request to", url, " - target - ", target)
            tries += 1
            _resp = cls.send_request(url)

            # if we get a 429, sleep for a bit and try again
            if _resp.status_code == 429 and cls.retry_429_tries > tries:
                print(
                    cls,
                    target,
                    f"got 429, sleeping for {cls.retry_429_interval} seconds",
                )
                time.sleep(cls.retry_429_interval)
            else:
                break

        return cls.process(target, url, _resp.status_code, lambda: _resp.json())

    @classmethod
    def send_request(cls, url):
        return requests.get(url)

    @classmethod
    def process(
        cls, target, url, http_status, getdata, payload=None, cached=False, content=None
    ):
        """
        processes a response and return the `Request` object created for it
        """

        source = cls.config("source_name")
        target_field = cls.config("target_field")
        response_cls = cls._meta.get_field("response").related_model

        params = {
            target_field: target,
            "url": url,
            "source": source,
            "type": cls.target_to_type(target),
        }

        if payload:
            params.update(payload=json.dumps(payload))

        try:
            req = cls.objects.get(**params)
            created = False
        except cls.DoesNotExist:
            req = cls(**params)
            created = True

        if not created:
            req.count += 1

        data = None

        req.http_status = http_status

        try:
            if callable(getdata):
                data = getdata()
            else:
                data = getdata
            req.processing_error = None
        except Exception as exc:
            req.processing_error = f"{exc}"

        if not cached:
            req.save()

        if data is not None:
            try:
                req.response
                create_response = False
            except Exception:
                create_response = True

            if not create_response:
                req.response.data = data
                req.response.content = content
                req.response.save()
            else:
                response_cls.objects.create(
                    source=source,
                    data=data,
                    content=content,
                    request=req,
                )

            # if a meta data class is defined for this request
            # we will write the meta data from the response

            try:
                if http_status in cls.valid_http_status:
                    req.response.write_meta_data(req)
            except NoMetaClassDefined:
                pass

            return req

        return req

    @classmethod
    def config(cls, config_name, default=None):
        value = getattr(cls.Config, config_name, default)

        if value is None:
            raise ValueError(f"`{cls}.Config.{config_name}` property not specified")

        return value

    @classmethod
    def get_cache(cls, target):
        qset = cls.get_cache_queryset(target)
        cached = qset.filter(updated__gte=cls.valid_cache_datetime(target)).first()

        if not cached:
            return None

        tdiff = time.time() - cached.updated.timestamp()

        # if the cached request is a 429 and it's older than 5 minutes we will ignore it and send a new request
        throttled_cache_expiry = cls.config("throttled_cache_expiry", 300)

        if cached.http_status == 429:
            cache_expiry = cls.cache_expiry(target)

            # if cache expiry is None (never expire) set it to throttled_cache_expiry
            if cache_expiry is None:
                cache_expiry = throttled_cache_expiry

            if tdiff > throttled_cache_expiry or tdiff > cache_expiry:
                # if the cached request is a 429 and it's older than 5 minutes or
                # older than the normal cache expiry we will ignore it and send a new request
                return None

        return cached

    @classmethod
    def get_cache_queryset(cls, target):
        target_field = cls.config("target_field")
        typ = cls.target_to_type(target)
        filters = {target_field: target, "source": cls.config("source_name")}

        if typ:
            filters.update(type=typ)
        else:
            filters.update(type__isnull=True)

        return cls.objects.filter(**filters)

    @classmethod
    def cache_expiry_from_settings(cls, target):
        """
        returns the cache expiry for the specified target from the settings
        """
        setting_name = f"{cls.config('source_name')}_cache_expiry".upper()

        # replace dash and spaces with underscore
        setting_name = re.sub(r"[\s-]", "_", setting_name)

        return getattr(settings, setting_name)

    @classmethod
    def cache_expiry(cls, target):
        # try to get the expiry from the settings
        try:
            expiry = cls.cache_expiry_from_settings(target)
        except AttributeError:
            expiry = cls.config("cache_expiry")

        return expiry

    @classmethod
    def valid_cache_datetime(cls, target):
        expiry = cls.cache_expiry(target)
        if expiry is None:
            # no cache expiry, return a date far in the past (100 years)
            return timezone.now() - timedelta(days=365 * 100)
        return timezone.now() - timedelta(seconds=expiry)

    def process_response(self, response, target, date):
        yield date, target, response.data

    def prepare_data(self, data):
        return data


class Response(HandleRefModel):

    """
    Maintains a cache for third party data responses
    """

    source = models.CharField(max_length=255)
    data = models.JSONField(null=True)
    content = models.TextField(
        help_text="raw content of response - may not be set if data and content are equal.",
        null=True,
        blank=True,
    )

    class Config:
        meta_data_cls = None
        attachment_cls = None

    class Meta:
        abstract = True

    class HandleRef:
        tag = "meta_response"

    @classmethod
    def config(cls, config_name, default=None):
        value = getattr(cls.Config, config_name, default)

        if value is None:
            raise ValueError(f"`{cls}.Config.{config_name}` property not specified")

        return value

    @property
    def meta_data_cls(self):
        try:
            return self.request.config("meta_data_cls", self.config("meta_data_cls"))
        except ValueError:
            raise NoMetaClassDefined()

    def write_meta_data(self, req):
        target_field = self.config("target_field", req.config("target_field"))
        source_name = req.config("source_name")
        target = getattr(req, target_field)

        had_entries = False

        for date, _target, data in req.process_response(self, target, timezone.now()):
            had_entries = True
            self._write_meta_data(
                req, date, req.prepare_data(data), _target, target_field, source_name
            )

        if not had_entries:
            # no entries were written, write an empty entry
            self._write_meta_data(
                req, timezone.now(), {}, target, target_field, source_name
            )

    def _write_meta_data(self, request, date, data, target, target_field, source_name):
        meta_data_cls = self.meta_data_cls

        meta_data_type = meta_data_cls.config("type")
        period = meta_data_cls.config("period")
        start = date - timedelta(seconds=period)
        end = date + timedelta(seconds=period)

        filters = {target_field: target, "source_name": source_name}
        meta_data = (
            meta_data_cls.objects.filter(date__gte=start, date__lte=end)
            .filter(**filters)
            .first()
        )

        if not meta_data:
            meta_data_recent = (
                meta_data_cls.objects.filter(**filters).order_by("-date").first()
            )
            if meta_data_recent and meta_data_recent.data == data:
                # while a meta data entry does not exist close to the date, the data is the same as the most recent entry

                # update the `updated` field of the most recent entry
                meta_data_recent.save()
                return

            # otherwise we create a new entry
            meta_data = meta_data_cls(data={}, source_name=source_name, date=date)
            setattr(meta_data, target_field, target)

        meta_data.data = data
        meta_data.type = meta_data_type

        meta_data.save()

    def add_attachment(self, file_name, file_data, content_type):
        attachment_cls = self.config("attachment_cls")

        return attachment_cls.objects.create(
            response=self,
            file_name=file_name,
            file_data=file_data,
            content_type=content_type,
        )


class Attachment(HandleRefModel):
    """
    File attachmnent for meta data response

    Needs to implement a `response` foreign key relationship to a `Response` class
    """

    content_type = models.CharField(max_length=255)
    file_data = models.BinaryField()
    file_name = models.CharField(max_length=255)

    class Meta:
        abstract = True

    class HandleRef:
        tag = "meta_attachment"

    @property
    def size(self):
        return len(self.file_data)
