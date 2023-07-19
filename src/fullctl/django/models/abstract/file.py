"""
Abstract models for database file storage.
"""

from django.db import models

from fullctl.django.models.abstract import HandleRefModel


class FileBase(HandleRefModel):
    name = models.CharField(max_length=255)
    content = models.BinaryField()
    content_type = models.CharField(max_length=255)
    public = models.BooleanField(default=False)

    class Meta:
        abstract = True

    class HandleRef:
        tag = "fullctl_file"
