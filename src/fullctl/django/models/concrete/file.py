"""
Concrete models for database file storage
"""

from django.db import models
from django_grainy.decorators import grainy_model

from fullctl.django.models.abstract.file import FileBase
from fullctl.django.models.concrete import Organization

__all__ = [
    "OrganizationFile",
]


@grainy_model(namespace="org", namespace_instance="org.{instance.org.permission_id}")
class OrganizationFile(FileBase):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE)

    class Meta:
        db_table = "fullctl_organization_file"
        verbose_name = "Organization File"
        verbose_name_plural = "Organization Files"

    class HandleRef:
        tag = "fullctl_organization_file"
