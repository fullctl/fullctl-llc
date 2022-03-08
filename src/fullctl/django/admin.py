import reversion
from django.contrib import admin
from django_handleref.admin import VersionAdmin

import fullctl.django.auditlog as auditlog
from fullctl.django.models.concrete import (
    AuditLog,
    Organization,
    OrganizationUser,
    Task,
    TaskSchedule,
)


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
        "param",
        "time",
        "user",
        "org",
        "created",
        "updated",
    )
    list_filter = ("status", "op")


@admin.register(TaskSchedule)
class TaskScheduleAdmin(BaseAdmin):
    readonly_fields = BaseAdmin.readonly_fields + ("tasks",)
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
        if obj and obj.log_object:
            return f"{obj.log_object}"
        elif obj and obj.object_id:
            return "<deleted>"
        return ""
