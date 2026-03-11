"""
DRF serializers for Case, Comment, AuditLog, and action endpoints.
"""

from rest_framework import serializers

from accounts.models import User
from accounts.serializers import UserSerializer

from .models import AuditLog, Case, Comment


class CaseSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)

    class Meta:
        model = Case
        fields = (
            "case_id",
            "title",
            "description",
            "priority",
            "status",
            "created_by",
            "assigned_to",
            "created_at",
            "updated_at",
            "version",
        )
        read_only_fields = (
            "case_id",
            "status",
            "created_by",
            "assigned_to",
            "created_at",
            "updated_at",
            "version",
        )


class CaseCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default="", allow_blank=True)
    priority = serializers.ChoiceField(
        choices=Case.Priority.choices, default=Case.Priority.MEDIUM
    )


class CaseUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=Case.Priority.choices, required=False)


class AssignCaseSerializer(serializers.Serializer):
    assigned_to = serializers.UUIDField()

    def validate_assigned_to(self, value):
        try:
            user = User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        if user.role != User.Role.REVIEWER:
            raise serializers.ValidationError(
                "Cases can only be assigned to users with the Reviewer role."
            )
        return value


class TransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Case.Status.choices)


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "case", "author", "content", "is_internal", "created_at")
        read_only_fields = ("id", "case", "author", "created_at")


class CommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField()
    is_internal = serializers.BooleanField(default=False)


class AuditLogSerializer(serializers.ModelSerializer):
    performed_by = UserSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = ("id", "case", "action", "performed_by", "details", "created_at")
        read_only_fields = fields
