from django.contrib import admin

from .models import AuditLog, Case, Comment


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = (
        "case_id",
        "title",
        "status",
        "priority",
        "created_by",
        "assigned_to",
        "created_at",
    )
    list_filter = ("status", "priority")
    search_fields = ("title", "description")
    readonly_fields = ("case_id", "created_at", "updated_at", "version")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "case", "author", "is_internal", "created_at")
    list_filter = ("is_internal",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "case", "action", "performed_by", "created_at")
    list_filter = ("action",)
    readonly_fields = ("id", "case", "action", "performed_by", "details", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
