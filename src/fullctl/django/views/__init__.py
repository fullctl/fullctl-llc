import datetime
import re
import sys

from django.conf import settings

# from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils.html import escape
from django.utils.safestring import mark_safe

from fullctl.django.decorators import require_auth


@require_auth()
def org_redirect(request):
    return redirect(f"/{request.org.slug}/")


def diag(request):
    if not request.user.is_superuser:
        raise Http404()

    txt = "HTTP Headers:\n"
    redact = ("KEY", "PASSWORD", "SECRET")
    for k, v in request.META.items():
        if any(re.findall(r"|".join(redact), k, re.IGNORECASE)):
            continue
        # if k.startswith("HTTP"):
        txt += f"{k}: {v}\n"

    return HttpResponse(mark_safe(f"<div><pre>Meta:\n{escape(txt)}</pre></div>"))


@require_auth()
def login(request):
    return redirect("/")


def logout(request):
    response = redirect(f"{settings.AAACTL_URL}/account/auth/logout/")
    request.session.delete()
    return response


def handle_error(request, exception, status):
    if exception:
        request.error_response = exception
        exc_type = exception.__class__
    else:
        exc_type, exception, tb = sys.exc_info()

    request.error_response = exception

    context = {
        "error": {
            "status": status,
            "type_description": f"{exc_type}",
            "description": f"{exception}",
            "path": request.path,
            "ip_address": request.META.get("HTTP_X_FORWARDED_FOR"),
            "referer": request.META.get("HTTP_REFERER"),
            "timestamp": datetime.datetime.utcnow(),
        }
    }

    response = render(request, f"common/errors/{status}.html", context)
    response.status_code = status
    return response


def handle_error_500(request, exception=None):
    return handle_error(request, exception, 500)


def handle_error_404(request, exception=None):
    return handle_error(request, exception, 404)


def handle_error_401(request, exception=None):
    return handle_error(request, exception, 401)


def handle_error_400(request, exception=None):
    return handle_error(request, exception, 400)


def handle_error_403(request, exception=None):
    return handle_error(request, exception, 403)
