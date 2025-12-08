import json
import re

import structlog
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test

# from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils.html import escape
from django.utils.http import http_date
from django.utils.safestring import mark_safe

import fullctl.django.health_check
import fullctl.service_bridge.aaactl as aaactl
from fullctl.django.decorators import require_auth
from fullctl.django.models.concrete.file import OrganizationFile
from fullctl.django.models.concrete.tasks import Task
from fullctl.django.util import error_context, load_branding_info

log = structlog.get_logger(__name__)


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


def healthcheck_verbose_response(results: dict) -> HttpResponse:
    html_lines = []
    all_ok = True

    for key, value in results.items():
        status = "ok" if value["ok"] else "failed"
        if "excluded" in value:
            html_lines.append(f"[+]{key} excluded: {status}")
        else:
            html_lines.append(f"[+]{key} {status}")
        all_ok = all_ok and value["ok"]

    if all_ok:
        html_lines.append("health check passed")
    else:
        html_lines.append("health check failed")

    html_content = "\n".join(html_lines)
    return HttpResponse(f"<pre>{html_content}</pre>", content_type="text/html")


def healthcheck(request):
    """
    Performs a simple database version query
    query params:
        exclude: list of health checks to exclude
        verbose: if true, return a verbose html response
    """
    exclude = request.GET.getlist("exclude", [])
    results = fullctl.django.health_check.check_all(exclude=exclude)
    verbose = "verbose" in request.GET
    if not verbose:
        return HttpResponse(json.dumps(results))
    return healthcheck_verbose_response(results)


def authcheck(request):
    """
    Checks if the user's access token is still valid

    The check itself is performed by middleware, status of the resonse
    will be set to 401 if the token is invalid. 200 otherwise.
    """

    if not request.user.is_authenticated:
        return HttpResponse("", status=401)

    return HttpResponse("")


@require_auth()
def login(request):
    return redirect("/")


def logout(request):
    response = redirect(f"{settings.AAACTL_URL}/account/auth/logout/")
    request.session.delete()
    return response


def fetch_branding(branding_org: str, request) -> aaactl.OrganizationBranding | None:
    org_branding = aaactl.OrganizationBranding().first(org=branding_org)
    if not org_branding:
        if http_host := request.get_host():
            org_branding = aaactl.OrganizationBranding().first(http_host=http_host)

    return org_branding


def handle_error(request, exception, status):
    context = {
        "error": error_context(status, exception, request),
        "org_branding": {},
        "is_error_page": True,
    }

    branding = load_branding_info(
        request, getattr(settings, "BRANDING_ORG", None), fetch_branding
    )

    if branding:
        context["org_branding"] = branding

    response = render(request, f"common/v2/errors/{status}.html", context)
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


def organization_file_download(request, org_tag, file_name):
    """
    Handles organization file downloads.

    This view is used to serve files that are stored in the database.

    The file is served as an attachment, with the original filename.

    If the file is not public, the user must have read access to the file
    """

    org_file = OrganizationFile.objects.get(name=file_name, org__slug=org_tag)

    if not org_file.public and not request.perms.check(org_file, "r"):
        return HttpResponse("", status=404)

    response = HttpResponse(org_file.content, content_type=org_file.content_type)
    response["Content-Disposition"] = f"attachment; filename={org_file.name}"

    # Set the Cache-Control header to instruct the browser to cache the response for 1 hour
    response["Cache-Control"] = "public, max-age=3600"

    # Set the Last-Modified header to the last modification time of the file
    response["Last-Modified"] = http_date(org_file.updated.timestamp())

    return response


@user_passes_test(lambda u: u.is_superuser)
def tasks_queue_status(request):
    # number of pending tasks
    pending_task = Task.objects.filter(status="pending", queue_id__isnull=False).count()

    # oldest pending task
    oldest_task = (
        Task.objects.filter(status="pending", queue_id__isnull=False)
        .order_by("created")
        .first()
    )

    # newest pending task
    newest_task = (
        Task.objects.filter(status="pending", queue_id__isnull=False)
        .order_by("-created")
        .first()
    )

    # last completed task
    last_completed_task = (
        Task.objects.filter(status="completed").order_by("-created").first()
    )

    # last 5 failed tasks
    failed_tasks = Task.objects.filter(status="failed").order_by("-created")[:5]

    tasks = {
        "pending_task": pending_task,
        "oldest_task": oldest_task,
        "newest_task": newest_task,
        "last_completed_task": last_completed_task,
        "failed_tasks": failed_tasks,
    }
    return render(request, "common/tasks_queue.html", {"tasks": tasks})
