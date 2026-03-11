"""
DRF permissions for role-based access control.
"""

from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Allow access only to users with the Admin role."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"


class IsAdminOrOperator(BasePermission):
    """Allow access to Admin and Operator roles."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            "admin",
            "operator",
        )


class IsAdminOrReviewer(BasePermission):
    """Allow access to Admin and Reviewer roles."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            "admin",
            "reviewer",
        )


class CanCreateCase(BasePermission):
    """Only Admin and Operator can create cases."""

    def has_permission(self, request, view):
        if request.method == "POST":
            return request.user.is_authenticated and request.user.role in (
                "admin",
                "operator",
            )
        return request.user.is_authenticated


class CanAssignCase(BasePermission):
    """Only Admin can assign cases."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"
