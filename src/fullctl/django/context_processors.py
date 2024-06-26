from datetime import datetime

import structlog
from django.conf import settings
from django.http import HttpRequest
from fullctl.django.auth import RemotePermissionsError
from fullctl.django.models.concrete.account import Organization
from fullctl.django.util import DEFAULT_FULLCTL_BRANDING
from fullctl.service_bridge.aaactl import OrganizationBranding, ServiceApplication

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


def request_can_see_service(request: HttpRequest, service_slug: str) -> bool:
    """
    Check if the requesting user has access to the service
    """

    if service_slug == "aaactl":
        # everyone has access to aaactl
        return True

    if service_slug == settings.SERVICE_TAG:
        # the user is requesting access to the service information
        # for the service that is currently being rendered
        return True

    org = getattr(request, "org", None)
    perms = getattr(request, "perms", None)

    if not org or not perms:
        # no organization or permissions object has been established
        # assume the user does not have access to the service
        return False

    return perms.check(f"service.{service_slug}.{org.permission_id}", "r")

def account_service(request):
    context = {}
    org = getattr(request, "org", None)
    context["org_branding"] = {}

    if org:
        org_slug = org.slug
    else:
        org_slug = ""

    local_auth = getattr(settings, "USE_LOCAL_PERMISSIONS", False)
    branding_override = getattr(settings, "BRANDING_ORG", None)
    branding = None

    # start by setting a default branding
    context["org_branding"] = DEFAULT_FULLCTL_BRANDING

    # if there is a branding_override set in the settings for the instance
    # use that (this is the highest priority branding setting)
    if branding_override:

        # SERVICE OVERRIDES BRANDING GLOBALLY

        branding = OrganizationBranding().first(org=branding_override)

        if not branding:
            log.warning(f"Using branding override: {branding_override}, but branding does not exist in aaactl")

    # otherwise check if the organization of the request has a branding applied
    # to it through aaactl (either on the org directly or through a BRANDING_ORG
    # set in aaactl)
    elif not branding:

        # AAACTL SELECTS BRANDING

        # using the `best` filter to get the most specific branding
        # this will either select the org's branding if it has one
        # or the branding set in the BRANDING_ORG setting
        branding = OrganizationBranding().first(best=org_slug)

        log.info("Branding AAACTL", branding=branding.json if branding else None, org_slug=org_slug)

    # last if there is no branding set yet, we would check http host
    # however for this to work some changes need to be made on the aaactl
    # side to support multiple hostnames (since services will be on different hosts)
    # TODO: supprt host for branding
    # http_host = request.get_host()

    # a branding was selected, prepare the context
    if branding:
        context["org_branding"] = {
            "name": branding.org_name,
            "html_footer": branding.html_footer,
            "css": branding.css,
            "dark_logo_url": branding.dark_logo_url,
            "light_logo_url": branding.light_logo_url,
            "custom_org": True,
            "show_logo": branding.show_logo,
        }

    if not context["org_branding"].get("dark_logo_url", None):
        service_logo_dark = f"{settings.SERVICE_TAG}/logo-darkbg.svg"
    else:
        service_logo_dark = context["org_branding"].get("dark_logo_url")

    if not context["org_branding"].get("light_logo_url", None):
        service_logo_light = f"{settings.SERVICE_TAG}/logo-lightbg.svg"
    else:
        service_logo_light = context["org_branding"].get("light_logo_url")

    if not context["org_branding"].get("name", None):
        logo_alt_text = settings.SERVICE_TAG
        service_name = settings.SERVICE_TAG.replace("ctl", "")
    else:
        logo_alt_text = context["org_branding"].get("name")
        service_name = context["org_branding"].get("name")

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
                # we call sanitize() to remove the `config` attribute
                # as that may contain sensitive information
                # that we don't necessarily want to expose to the template
                # context
                service_application.for_org(org).sanitize()
                for service_application in ServiceApplication().objects(
                    group="fullctl", org=(org_slug or None)
                )
                # only show services that the user has access to
                if request_can_see_service(request, service_application.slug)
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
            "name": f"{settings.SERVICE_TAG} {context['org_branding']['name']}"
            if context["org_branding"].get("name", None)
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
