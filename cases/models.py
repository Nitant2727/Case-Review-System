import uuid

from django.conf import settings
from django.db import models


class Case(models.Model):
    """Represents a case in the review workflow."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_REVIEW = "pending_review", "Pending Review"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CLOSED = "closed", "Closed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    # Allowed status transitions: source -> set of valid targets
    ALLOWED_TRANSITIONS = {
        Status.DRAFT: {Status.PENDING_REVIEW},
        Status.PENDING_REVIEW: {Status.IN_REVIEW},
        Status.IN_REVIEW: {Status.APPROVED, Status.REJECTED},
        Status.APPROVED: {Status.CLOSED},
        Status.REJECTED: {Status.CLOSED},
    }

    case_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_cases",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_cases",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Optimistic concurrency control
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "cases"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"

    def can_transition_to(self, new_status: str) -> bool:
        """Check if the transition from current status to new_status is allowed."""
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        return new_status in allowed


class Comment(models.Model):
    """Comment on a case. May be internal (visible only to Admin/Reviewer)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="comments"
    )
    content = models.TextField()
    is_internal = models.BooleanField(
        default=False,
        help_text="Internal comments are visible only to Admin and Reviewer.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comments"
        ordering = ["-created_at"]

    def __str__(self):
        visibility = "internal" if self.is_internal else "public"
        return f"Comment by {self.author} on {self.case} ({visibility})"


class AuditLog(models.Model):
    """
    Immutable audit trail for important actions.
    Tracked actions: assignment, status_change, comment_added, case_created.
    """

    class Action(models.TextChoices):
        CASE_CREATED = "case_created", "Case Created"
        STATUS_CHANGE = "status_change", "Status Change"
        ASSIGNMENT = "assignment", "Assignment"
        COMMENT_ADDED = "comment_added", "Comment Added"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=30, choices=Action.choices)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="audit_logs"
    )
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        # Prevent updates/deletes at Django level
        # (we also add DB-level protection via save override)

    def save(self, *args, **kwargs):
        """Audit logs are immutable – only allow creation, never updates."""
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("Audit logs are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit logs are immutable and cannot be deleted.")

    def __str__(self):
        return f"[{self.get_action_display()}] {self.case} by {self.performed_by}"
