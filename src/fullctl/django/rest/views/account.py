from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

import fullctl.django.models as models
import fullctl.django.rest.throttle as throttle
import fullctl.service_bridge.aaactl as aaactl
from fullctl.django.rest.decorators import grainy_endpoint
from fullctl.django.rest.route.account import route
from fullctl.django.rest.serializers import EmptySerializer
from fullctl.django.rest.serializers.account import Serializers
from fullctl.django.util import verified_asns


@route
class Organization(viewsets.GenericViewSet):

    """
    Manage user's organizations
    """

    serializer_class = Serializers.org
    queryset = models.Organization.objects.all()

    def list(self, request, *args, **kwargs):
        """
        List the organizations that the requesting user belongs
        to or has permissions to
        """

        serializer = Serializers.org(
            instance=models.Organization.accessible(request.user),
            many=True,
            context={"user": request.user},
        )
        return Response(serializer.data)


@route
class User(viewsets.GenericViewSet):
    ref_tag = "user"
    serializer_class = Serializers.asn

    @action(detail=False, methods=["GET"])
    @grainy_endpoint()
    def asns(self, request, org, *args, **kwargs):
        """
        Lists the asns that the requesting user has been verified for.
        """

        serializer = Serializers.asn(verified_asns(request.perms), many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["POST"], serializer_class=EmptySerializer)
    def stop_impersonation(self, request, *args, **kwargs):
        """
        Stop impersonating a user via the aaactl service bridge
        """

        if not getattr(request, "impersonating", None):
            return Response({})

        try:
            del request.session["impersonating"]
        except KeyError:
            pass

        aaactl.Impersonation().stop(
            request.impersonating["superuser"].social_auth.first().uid
        )

        return Response({})

    @action(
        detail=False,
        methods=["POST"],
        serializer_class=Serializers.contact_message,
        throttle_classes=[throttle.ContactMessage],
    )
    def contact_support(self, request, *args, **kwargs):
        """
        Contact support through aaactl
        """

        serializer = Serializers.contact_message(
            data=request.data, context={"user": request.user}
        )
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(serializer.data)
