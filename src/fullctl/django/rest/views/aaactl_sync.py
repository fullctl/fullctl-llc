"""
API views to facilitate data synchronization from aaactl to the fullctl
service.

These views require permissions to the `aaactl_sync` namespace which usually
only exists on the internal api key used for service bridging
"""

from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.response import Response

import fullctl.django.models as models
from fullctl.django.rest.core import BadRequest
from fullctl.django.rest.decorators import grainy_endpoint
from fullctl.django.rest.mixins import CachedObjectMixin
from fullctl.django.rest.route.service_bridge import route
from fullctl.django.rest.serializers.aaactl_sync import Serializers


@route
class User(CachedObjectMixin, viewsets.GenericViewSet):

    """
    Sync user information from aaactl using the service bridge

    - username
    - email
    - first name
    - last name
    """

    path_prefix = "/aaactl-sync"
    serializer_class = Serializers.user
    queryset = get_user_model().objects.all()

    # this approach assumes that aaactl is the only authentication
    # provider
    lookup_field = "social_auth__uid"
    lookup_url_kwarg = "remote_id"

    @grainy_endpoint("aaactl_sync.user")
    def update(self, request, remote_id, *args, **kwargs):
        user = self.get_object()
        serializer = self.serializer_class(instance=user, data=request.data)
        if not serializer.is_valid():
            return BadRequest(serializer.errors)
        serializer.save()
        return Response(serializer.data)


@route
class Organization(CachedObjectMixin, viewsets.GenericViewSet):

    """
    Sync organization information from aaactl using the service
    brdige

    - name
    - url slug
    """

    path_prefix = "/aaactl-sync"
    serializer_class = Serializers.org
    queryset = models.Organization.objects.all()
    lookup_field = "remote_id"
    lookup_url_kwarg = "remote_id"

    @grainy_endpoint("aaactl_sync.org")
    def create(self, request, *args, **kwargs):
        try:
            instance = models.Organization.objects.get(
                remote_id=request.data["remote_id"]
            )
        except models.Organization.DoesNotExist:
            instance = None
        serializer = self.serializer_class(instance=instance, data=request.data)

        if not serializer.is_valid():
            return BadRequest(serializer.errors)
        serializer.save()
        return Response(serializer.data)


@route
class OrganizationUser(CachedObjectMixin, viewsets.GenericViewSet):

    """
    Sync organization<->user relationships from aaactl using the service
    bridge
    """

    path_prefix = "/aaactl-sync"
    serializer_class = Serializers.org_user
    queryset = get_user_model().objects.all()

    # this approach assumes that aaactl is the only authentication
    # provider
    lookup_field = "social_auth__uid"
    lookup_url_kwarg = "remote_id"

    @grainy_endpoint("aaactl_sync.org_user")
    def update(self, request, remote_id, *args, **kwargs):
        self.get_object()
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return BadRequest(serializer.errors)
        serializer.save()
        return Response(serializer.data)
