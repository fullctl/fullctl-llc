from datetime import datetime

from django.conf import settings

from fullctl.django.auth import RemotePermissionsError
from fullctl.service_bridge.aaactl import ServiceApplication


def conf(request):
    return {
        "google_analytics_id": getattr(settings, "GOOGLE_ANALYTICS_ID", None),
        "cloudflare_analytics_id": getattr(settings, "CLOUDFLARE_ANALYTICS_ID", "asdf"),
        "support_email": settings.SUPPORT_EMAIL,
        "contact_us_email": settings.CONTACT_US_EMAIL,
        "no_reply_email": settings.NO_REPLY_EMAIL,
        "post_feature_request_url": settings.POST_FEATURE_REQUEST_URL,
        "docs_url": settings.DOCS_URL,
        "legal_url": settings.LEGAL_URL,
        "current_year": datetime.now().year,
    }


def account_service(request):
    context = {}
    org = getattr(request, "org", None)

    if org:
        org_slug = org.slug
    else:
        org_slug = ""

    # TODO abstract so other auth services can be
    # defined
    context.update(
        account_service={
            "urls": {
                "billing_setup": f"{settings.OAUTH_TWENTYC_URL}/billing/setup?org={org_slug}",
                "manage_account": f"{settings.OAUTH_TWENTYC_URL}/account/?edit=account",
                # TODO: flesh out to redirect to org/create
                "create_org": f"{settings.OAUTH_TWENTYC_URL}/account/",
                "manage_org": f"{settings.OAUTH_TWENTYC_URL}/account/?org={org_slug}",
            },
        },
        # TODO: deprecated
        oauth_manages_org=True,
        service_logo_dark=f"{settings.SERVICE_TAG}/logo-darkbg.svg",
        service_logo_light=f"{settings.SERVICE_TAG}/logo-lightbg.svg",
        service_tag=settings.SERVICE_TAG,
        service_name=settings.SERVICE_TAG.replace("ctl", ""),
    )

    if settings.OAUTH_TWENTYC_URL:
        context.update(
            service_applications=[
                service_application.for_org(org)
                for service_application in ServiceApplication().objects(
                    group="fullctl", org=(org_slug or None)
                )
            ],
        )

    # load this applications information from aaactl
    # into `service_info` variable

    for svc_app in context.get("service_applications", []):
        if svc_app.slug != settings.SERVICE_TAG:
            continue

        context.update(service_info=svc_app)
        break

    return context


def permissions(request):
    # in case of a RemotePermissionsError being set in the
    # `error_response` attribute of the request, we DO NOT
    # want to attempt to retrieve permissions again
    #
    # at this point we are looking to render an error page

    error_response = getattr(request, "error_response", False)
    if isinstance(error_response, RemotePermissionsError):
        return {"permissions": {}}

    context = {}

    ops = [("c", "create"), ("r", "read"), ("u", "update"), ("d", "delete")]

    if not hasattr(request, "org"):
        return {"permissions": {}}

    is_accessible = request.org in request.org.accessible(request.user)

    for op, name in ops:
        key = f"{name}_instance"
        if name == "read":
            context[key] = is_accessible
        else:
            context[key] = request.perms.check(request.org, op)

    context["billing"] = request.perms.check(
        f"billing.{request.org.permission_id}", "c"
    )

    return {"permissions": context}
