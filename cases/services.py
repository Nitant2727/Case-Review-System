"""
Business logic / service layer for case workflow operations.

Centralising workflow logic here keeps views thin and makes
the rules easy to test in isolation.
"""

from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.models import User

from .models import AuditLog, Case, Comment
from .tasks import send_notification


def create_case(
    *,
    user: User,
    title: str,
    description: str = "",
    priority: str = Case.Priority.MEDIUM,
) -> Case:
    """Create a new case. Only Admin and Operator may create cases."""
    if user.role not in (User.Role.ADMIN, User.Role.OPERATOR):
        raise PermissionDenied("Only Admin and Operator can create cases.")

    with transaction.atomic():
        case = Case.objects.create(
            title=title,
            description=description,
            priority=priority,
            created_by=user,
        )
        AuditLog.objects.create(
            case=case,
            action=AuditLog.Action.CASE_CREATED,
            performed_by=user,
            details={"title": title, "priority": priority},
        )
    return case


def assign_case(*, case: Case, assignee: User, performed_by: User) -> Case:
    """Assign a case to a reviewer. Only Admin can assign."""
    if not performed_by.is_admin:
        raise PermissionDenied("Only Admin can assign cases.")

    if assignee.role != User.Role.REVIEWER:
        raise ValidationError(
            "Cases can only be assigned to users with the Reviewer role."
        )

    with transaction.atomic():
        old_assignee = case.assigned_to
        case.assigned_to = assignee
        case.save(update_fields=["assigned_to", "updated_at"])

        AuditLog.objects.create(
            case=case,
            action=AuditLog.Action.ASSIGNMENT,
            performed_by=performed_by,
            details={
                "old_assigned_to": str(old_assignee.id) if old_assignee else None,
                "new_assigned_to": str(assignee.id),
                "assignee_username": assignee.username,
            },
        )

    # Async notification
    send_notification.delay(
        event="assignment",
        case_id=str(case.case_id),
        recipient_id=str(assignee.id),
        details={"assigned_by": performed_by.username, "case_title": case.title},
    )
    return case


def transition_case(*, case: Case, new_status: str, performed_by: User) -> Case:
    """
    Transition a case to a new status with strict validation.
    Uses select_for_update for transaction-safe concurrency control.
    """
    if new_status not in Case.Status.values:
        raise ValidationError(f"Invalid status: {new_status}")

    with transaction.atomic():
        # Lock the row to prevent concurrent updates
        locked_case = Case.objects.select_for_update().get(pk=case.pk)

        if not locked_case.can_transition_to(new_status):
            raise ValidationError(
                f"Cannot transition from '{locked_case.get_status_display()}' "
                f"to '{Case.Status(new_status).label}'."
            )

        # Cannot move to in_review unless assigned
        if new_status == Case.Status.IN_REVIEW and locked_case.assigned_to is None:
            raise ValidationError(
                "Case cannot move to 'In Review' unless it is assigned to a reviewer."
            )

        # Reviewer can only review cases assigned to them
        if new_status in (
            Case.Status.IN_REVIEW,
            Case.Status.APPROVED,
            Case.Status.REJECTED,
        ):
            if performed_by.is_reviewer and locked_case.assigned_to != performed_by:
                raise PermissionDenied(
                    "Reviewer can only review cases assigned to them."
                )

        old_status = locked_case.status
        locked_case.status = new_status
        locked_case.version = F("version") + 1
        locked_case.save(update_fields=["status", "version", "updated_at"])

        AuditLog.objects.create(
            case=locked_case,
            action=AuditLog.Action.STATUS_CHANGE,
            performed_by=performed_by,
            details={"old_status": old_status, "new_status": new_status},
        )

    # Refresh to get the updated version value
    locked_case.refresh_from_db()

    # Async notification for review outcomes
    if new_status in (Case.Status.APPROVED, Case.Status.REJECTED):
        send_notification.delay(
            event="review_outcome",
            case_id=str(locked_case.case_id),
            recipient_id=str(locked_case.created_by_id),
            details={
                "outcome": new_status,
                "reviewed_by": performed_by.username,
                "case_title": locked_case.title,
            },
        )

    return locked_case


def add_comment(
    *, case: Case, author: User, content: str, is_internal: bool = False
) -> Comment:
    """Add a comment to a case with audit logging."""
    with transaction.atomic():
        comment = Comment.objects.create(
            case=case,
            author=author,
            content=content,
            is_internal=is_internal,
        )
        AuditLog.objects.create(
            case=case,
            action=AuditLog.Action.COMMENT_ADDED,
            performed_by=author,
            details={
                "comment_id": str(comment.id),
                "is_internal": is_internal,
            },
        )
    return comment
