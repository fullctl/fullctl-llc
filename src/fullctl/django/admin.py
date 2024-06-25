import reversion
from django.contrib import admin, messages
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import path, re_path, reverse
from django.utils.html import format_html
from django.utils.translation import ngettext as _
from django_handleref.admin import VersionAdmin

import fullctl.django.auditlog as auditlog
from fullctl.django.models.concrete import (
    Attachment,
    AuditLog,
    Organization,
    OrganizationFile,
    OrganizationUser,
    Request,
    Response,
    Task,
    TaskClaim,
    TaskSchedule,
    UserSettings,
)
from fullctl.django.models.concrete.service_bridge import ServiceBridgeAction
from fullctl.django.tasks import requeue as requeue_task


class BaseAdmin(VersionAdmin):
    readonly_fields = ("version",)

    def save_model(self, request, obj, form, change):
        with auditlog.Context() as ctx:
            ctx.set("user", request.user)
            ctx.set("info", "django-admin")
            with reversion.create_revision():
                return super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        with auditlog.Context() as ctx:
            ctx.set("user", request.user)
            ctx.set("info", "django-admin")
            with reversion.create_revision():
                return super().save_formset(request, form, formset, change)


class BaseTabularAdmin(admin.TabularInline):
    readonly_fields = ("version",)


class OrganizationUserInline(admin.TabularInline):
    model = OrganizationUser
    extra = 1
    fields = ("status", "user", "is_default")


@admin.register(Organization)
class OrganizationAdmin(BaseAdmin):
    list_display = ("id", "name", "slug")
    inlines = (OrganizationUserInline,)


@admin.register(OrganizationFile)
class OrganizationFileAdmin(BaseAdmin):
    list_display = (
        "id",
        "name",
        "org",
        "public",
        "created",
        "updated",
        "download_link",
    )
    search_fields = ("name", "org__name")

    def download_link(self, obj):
        return format_html(
            '<a href="{}">Download</a>', reverse("admin:download_file", args=[obj.pk])
        )

    download_link.short_description = "Download Link"

    def download_file(self, request, pk):
        file = self.get_object(request, pk)
        response = FileResponse(
            file.content,
            as_attachment=True,
            filename=file.name,
            content_type=file.content_type,
        )
        return response

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:pk>/download/",
                self.admin_site.admin_view(self.download_file),
                name="download_file",
            ),
        ]
        return custom_urls + urls


class TaskClaimInline(BaseTabularAdmin):
    model = TaskClaim
    extra = 0


@admin.register(Task)
class TaskAdmin(BaseAdmin):
    list_display = (
        "id",
        "source",
        "queue_id",
        "parent",
        "status",
        "op",
        "limit_id",
        # Params can ge quite large at this point, maybe we
        # hide it by default? Could do display up to a certain length
        # "param",
        "time",
        "user",
        "org",
        "created",
        "updated",
        "requeued",
    )
    list_filter = ("status", "op")
    actions = ["requeue_tasks"]
    # auto complete
    raw_id_fields = ("parent", "user", "org")
    inlines = (TaskClaimInline,)

    def requeue_tasks(self, request, queryset):
        """
        Custom action to re-queue tasks. This will unset the queue_id and delete the task claim.
        """
        for task in queryset:
            requeue_task(task)
        self.message_user(
            request,
            _(
                "%d task was successfully re-queued.",
                "%d tasks were successfully re-queued.",
                len(queryset),
            )
            % len(queryset),
            messages.SUCCESS,
        )

    requeue_tasks.short_description = "Re-queue selected tasks"


@admin.register(TaskSchedule)
class TaskScheduleAdmin(BaseAdmin):
    readonly_fields = BaseAdmin.readonly_fields + ("recent_tasks",)
    list_display = (
        "id",
        "description",
        "status",
        "interval",
        "repeat",
        "user",
        "org",
        "created",
        "updated",
        "schedule",
    )
    exclude = ("tasks",)

    def recent_tasks(self, obj):
        tasks = obj.tasks.all()[:5]
        return f"{tasks}"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "action",
        "object_type",
        "object_id",
        "log_object",
        "org",
        "user",
        "key",
        "info",
        "created",
    )

    readonly_fields = ("log_object",)

    search_fields = (
        "info",
        "org__name",
        "key",
        "user__username",
        "user__email",
        "object_id",
    )
    list_filter = ("action", "object_type")

    def log_object(self, obj=None):
        if obj and getattr(obj, "log_object", None):
            return f"{obj.log_object}"
        elif obj and obj.object_id:
            return "<deleted>"
        return ""


class UrlActionMixin:
    def make_redirect(self, obj, action):
        opts = obj.model._meta
        return redirect(f"admin:{opts.app_label}_{opts.model_name}_changelist")

    def actions_view(self, request, object_id, action, **kwargs):
        """
        Allows one to call any actions defined in this model admin
        to be called via an admin view placed at <model_name>/<id>/<action>/<action_name>.
        """
        obj = self.get_queryset(request).filter(pk=object_id)
        if obj.exists():
            redir = self.make_redirect(obj, action)
            action = self.get_action(action)
            if action:
                
                # action function found, next check if the user has
                # permission to perform the action
                permissions = action[0].allowed_permissions
                allowed = False

                # if the user passes any of the permissions, allow the action
                for perm in permissions:
                    fn_check_perm  = getattr(self, f"has_{perm}_permission")
                    allowed = fn_check_perm(request)
                    if allowed:
                        break
                
                if not allowed:
                    # user does not have permission to perform the action
                    return HttpResponseForbidden("You do not have permission to perform this action")

                action[0](self, request, obj)
                return redir
        return redirect(
            "admin:%s_%s_changelist"
            % (obj.model._meta.app_label, obj.model._meta.model_name)
        )

    def get_urls(self):
        """
        Adds the actions view as a subview of this model's admin views.
        """
        info = self.model._meta.app_label, self.model._meta.model_name

        urls = [
            re_path(
                r"^(\d+)/action/([\w]+)/$",
                self.admin_site.admin_view(self.actions_view),
                name="%s_%s_actions" % info,
            ),
        ] + super().get_urls()
        return urls


@admin.register(ServiceBridgeAction)
class ServiceBridgeAction(admin.ModelAdmin):
    list_display = (
        "name",
        "reference",
        "target",
        "action",
        "function",
        "description",
        "created",
        "updated",
    )


@admin.register(UserSettings)
class UserSettingsAdmin(BaseAdmin):
    list_display = ("user", "theme", "color_scheme")


class ResponseInline(admin.TabularInline):
    model = Response
    extra = 0
    show_change_link = True


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    readonly_fields = ["size"]


@admin.register(Request)
class RequestAdmin(BaseAdmin):
    list_display = [
        "identifier",
        "source",
        "type",
        "http_status",
        "count",
        "created",
        "updated",
    ]
    list_filter = ["http_status", "source", "type"]
    inlines = [
        ResponseInline,
    ]
    search_fields = [
        "identifier",
    ]


@admin.register(Response)
class ResponseAdmin(BaseAdmin):
    list_display = [
        "request",
        "created",
        "updated",
    ]
    inlines = [
        AttachmentInline,
    ]
    search_fields = [
        "request__identifier",
    ]
