"""
Implements request and response models for universal non-specific
requests and responses using the meta-data request caching system
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from fullctl.django.models.abstract.meta import Attachment as BaseAttachment
from fullctl.django.models.abstract.meta import Request as BaseRequest
from fullctl.django.models.abstract.meta import Response as BaseResponse

__all__ = [
    "Request",
    "Response",
    "Attachment",
]


class Request(BaseRequest):
    """
    request model
    """

    identifier = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = "request"
        verbose_name = _("Request")
        verbose_name_plural = _("Requests")

    class HandleRef:
        tag = "request"

    class Config:
        source_name = "generic"
        cache_expiry = 86400
        target_field = "identifier"


class Response(BaseResponse):
    """
    response model
    """

    request = models.OneToOneField(
        Request,
        on_delete=models.CASCADE,
        related_name="response",
    )

    class Meta:
        db_table = "meta_response"
        verbose_name = _("Response")
        verbose_name_plural = _("Responses")

    class HandleRef:
        tag = "response"

    class Config:
        meta_data_cls = None
        attachment_cls = None


class Attachment(BaseAttachment):

    """
    file attachment model
    """

    response = models.ForeignKey(
        Response, on_delete=models.CASCADE, related_name="attachments"
    )

    class Meta:
        db_table = "meta_attachment"
        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")

    class HandleRef:
        tag = "attachment"


Response.Config.attachment_cls = Attachment
