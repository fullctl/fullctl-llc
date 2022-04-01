"""
Abstract classes to facilitate the fetching, caching and retrieving of meta data
sourced from third party sources.
"""
from datetime import timedelta
from django.util import timezone
from fullctl.django.models.abstract import HandleRefModel

__all__ = [
    "Request",
    "Response",
    "Data",
]


class Data(HandleRefModel):

    """
    Normalized object meta data
    """

    meta = models.JSONField()

    class Meta:
        abstract = True

    class HandleRef:
        tag = "meta_data"


class Request(HandleRefModel):

    """
    Handles logic for requesting and rate-throttling third party meta data
    """

    source = models.CharField(max_length=255)
    url = models.URLField()
    http_status = models.PositiveIntegerField()
    payload = models.JSONField(null=True)

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
            results[target] = cls.request_target(target)

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
            if request.response_id:
                return request.response
            return request

        return cls.send(target)

    @classmethod
    def target_to_url(cls, target):

        """
        override this to handle converting a target to a requestable url
        """

        raise NotImplementedError()

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

        _resp = requests.get(url)

        return cls.process(target, url, _resp.status_code, lambda: _resp.json())

    @classmethod
    def process(cls, target, url, http_status, getdata, payload=None):

        """
        processes a response and return the `Request` object created for it
        """

        source = cls.config("source_name")
        response_cls = cls._meta.get_field("response").related_model

        params = {"pk": target, "url": url, "source": source}

        if paload:
            params.update(payload=json.dumps(payload))

        req, _ = cls.objects.get_or_create(**params)
        req.http_status = http_response.status_code

        data = None

        try:
            if callable(getdata):
                data = getdata()
            else:
                data = getdata
        except Exception as exc:
            req.processing_error = f"{exc}"

        req.save()

        if data is not None:

            if req.response_id:
                req.response.data = data
                req.response.save()
            else:
                response_cls.objects.create(
                    source=source,
                    data=data,
                    request=req,
                )

            req.response.write_meta_data()

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
        qset = qset.filter(updated__gte=cls.valid_cache_datetime())

        if qset.exists():
            return qset.first()

        return None

    @classmethod
    def get_cache_queryset(cls, target):
        return cls.objects.filter(pk=target)

    @classmethod
    def valid_cache_datetime(cls):
        expiry = cls.config("cache_expiry")
        return timezone.now() - timedelta(minutes=expiry)


class Response(HandleRefModel):

    """
    Maintains a cache for third party data responses
    """

    source = models.CharField(max_length=255)
    data = models.JSONField(null=True)

    class Config:
        meta_data_cls = None

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

    def prepare_meta_data(self):
        raise NotImplementedError("override in extended class")

    def write_meta_data(self):

        meta_data_cls = self.config("meta_data_cls")
        meta_data, _ = meta_data_cls.objects.get_or_create(pk=self.pk)
        meta_data.data.update(self.prepare_meta_data() or {})
        meta_data.save()
