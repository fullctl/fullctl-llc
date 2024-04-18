import json
from datetime import datetime

import structlog
from django.conf import settings

from fullctl.django.auth import RemotePermissionsError
from fullctl.django.models.concrete.account import Organization
from fullctl.django.util import DEFAULT_FULLCTL_BRANDING
from fullctl.service_bridge.aaactl import OrganizationWhiteLabeling, ServiceApplication

log = structlog.get_logger("django")


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
        "terms_of_service_url": settings.TERMS_OF_SERVICE_URL,
        "current_year": datetime.now().year,
    }


def account_service(request):
    context = {}
    org = getattr(request, "org", None)
    context["org_whitelabel"] = {}

    if org:
        org_slug = org.slug
    else:
        org_slug = ""

    local_auth = getattr(settings, "USE_LOCAL_PERMISSIONS", False)
    BRANDING_ORG = settings.BRANDING_ORG
    HTTP_HOST = request.get_host()

    try:
        # TODO: Look into appreach to return org specific whitelabel or default whitelabel
        org_whitelabel = OrganizationWhiteLabeling().first(org=org_slug)
        organization = Organization.objects.get(slug=org_slug)
        custom_org = True

        if not org_whitelabel:
            if BRANDING_ORG:
                org_whitelabel = OrganizationWhiteLabeling.objects.filter(
                    org=BRANDING_ORG
                ).first()
                if org_whitelabel:
                    organization = Organization.objects.get(slug=BRANDING_ORG)
                    css_dict = (
                        json.loads(org_whitelabel.css) if org_whitelabel.css else {}
                    )
            elif HTTP_HOST:
                org_whitelabel = OrganizationWhiteLabeling.objects.filter(
                    http_host=HTTP_HOST
                ).first()
                if org_whitelabel:
                    organization = Organization.objects.get(slug=org_slug)
                    css_dict = (
                        json.loads(org_whitelabel.css) if org_whitelabel.css else {}
                    )
        else:
            css_dict = json.loads(org_whitelabel.css) if org_whitelabel.css else {}

        if org_whitelabel and organization:
            context["org_whitelabel"] = {
                "name": organization.name,
                "html_footer": org_whitelabel.html_footer,
                "css": css_dict,
                "dark_logo_url": org_whitelabel.dark_logo_url,
                "light_logo_url": org_whitelabel.light_logo_url,
                "custom_org": custom_org,
                "show_logo": org_whitelabel.show_logo,
            }

        if not org_whitelabel and not BRANDING_ORG and not HTTP_HOST:
            context["org_whitelabel"] = DEFAULT_FULLCTL_BRANDING

    except Exception as e:
        log.error(f"Error fetching org whitelabel: {e}")
        context["org_whitelabel"] = DEFAULT_FULLCTL_BRANDING

    if not context["org_whitelabel"].get("dark_logo_url", None):
        service_logo_dark = f"{settings.SERVICE_TAG}/logo-darkbg.svg"
    else:
        service_logo_dark = context["org_whitelabel"].get("dark_logo_url")

    if not context["org_whitelabel"].get("light_logo_url", None):
        service_logo_light = f"{settings.SERVICE_TAG}/logo-lightbg.svg"
    else:
        service_logo_light = context["org_whitelabel"].get("light_logo_url")

    if not context["org_whitelabel"].get("name", None):
        logo_alt_text = settings.SERVICE_TAG
        service_name = settings.SERVICE_TAG.replace("ctl", "")
    else:
        logo_alt_text = context["org_whitelabel"].get("name")
        service_name = context["org_whitelabel"].get("name")

    service_tag = settings.SERVICE_TAG

    # TODO abstract so other auth services can be
    # defined
    context.update(
        account_service={
            "urls": {
                "billing_setup": f"{settings.OAUTH_TWENTYC_URL}/billing/setup?org={org_slug}",
                "manage_account": f"{settings.OAUTH_TWENTYC_URL}/account/",
                # TODO: flesh out to redirect to org/create
                "create_org": f"{settings.OAUTH_TWENTYC_URL}/account/",
                "manage_org": f"{settings.OAUTH_TWENTYC_URL}/account/?org=org_slug",
            },
        },
        oauth_manages_org=not local_auth,
        service_logo_dark=service_logo_dark,
        service_logo_light=service_logo_light,
        service_tag=service_tag,
        service_name=service_name,
        logo_alt_text=logo_alt_text,
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

    if local_auth:
        context["service_info"] = {
            "name": f"{settings.SERVICE_TAG} {context['org_whitelabel']['name']}"
            if context["org_whitelabel"].get("name", None)
            else settings.SERVICE_TAG,
            "slug": settings.SERVICE_TAG,
            "description": "Local permissions",
            "org_has_access": True,
            "org_namespace": settings.SERVICE_TAG,
        }

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


def trial_available(request):
    """
    Returns a boolean indicating whether or not there is a trial
    available for the requesting organization at the service
    """

    service = ServiceApplication()

    return {
        "trial_available": service.trial_available(
            {
                "org_slug": request.org.slug,
                "service_slug": settings.SERVICE_TAG,
            }
        )
    }
