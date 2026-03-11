from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (("Role", {"fields": ("role",)}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (("Role", {"fields": ("role",)}),)
