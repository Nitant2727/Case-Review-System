"""
Tests for the service layer – covers all critical business rules.
"""

import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError

from cases.models import AuditLog, Case, Comment
from cases.services import add_comment, assign_case, create_case, transition_case

from . import (
    AdminUserFactory,
    CaseFactory,
    OperatorUserFactory,
    ReviewerUserFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestCreateCase:
    """Only Admin and Operator can create cases."""

    def test_operator_can_create_case(self):
        user = OperatorUserFactory()
        case = create_case(user=user, title="Test Case")
        assert case.title == "Test Case"
        assert case.status == Case.Status.DRAFT
        assert case.created_by == user

    def test_admin_can_create_case(self):
        user = AdminUserFactory()
        case = create_case(user=user, title="Admin Case", priority=Case.Priority.HIGH)
        assert case.priority == Case.Priority.HIGH

    def test_reviewer_cannot_create_case(self):
        user = ReviewerUserFactory()
        with pytest.raises(PermissionDenied):
            create_case(user=user, title="Should Fail")

    def test_case_creation_creates_audit_log(self):
        user = OperatorUserFactory()
        case = create_case(user=user, title="Audited Case")
        log = AuditLog.objects.filter(case=case, action=AuditLog.Action.CASE_CREATED)
        assert log.exists()
        assert log.first().performed_by == user


@pytest.mark.django_db
class TestAssignCase:
    """Only Admin can assign cases; only to Reviewers."""

    def test_admin_can_assign_to_reviewer(self):
        admin = AdminUserFactory()
        reviewer = ReviewerUserFactory()
        case = CaseFactory(created_by=admin)

        updated = assign_case(case=case, assignee=reviewer, performed_by=admin)
        assert updated.assigned_to == reviewer

    def test_non_admin_cannot_assign(self):
        operator = OperatorUserFactory()
        reviewer = ReviewerUserFactory()
        case = CaseFactory(created_by=operator)

        with pytest.raises(PermissionDenied):
            assign_case(case=case, assignee=reviewer, performed_by=operator)

    def test_cannot_assign_to_non_reviewer(self):
        admin = AdminUserFactory()
        operator = OperatorUserFactory()
        case = CaseFactory(created_by=admin)

        with pytest.raises(ValidationError):
            assign_case(case=case, assignee=operator, performed_by=admin)

    def test_assignment_creates_audit_log(self):
        admin = AdminUserFactory()
        reviewer = ReviewerUserFactory()
        case = CaseFactory(created_by=admin)

        assign_case(case=case, assignee=reviewer, performed_by=admin)
        log = AuditLog.objects.filter(case=case, action=AuditLog.Action.ASSIGNMENT)
        assert log.exists()
        assert log.first().details["new_assigned_to"] == str(reviewer.id)


@pytest.mark.django_db
class TestTransitionCase:
    """Status transitions with strict validation."""

    def test_valid_transition_draft_to_pending_review(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin, status=Case.Status.DRAFT)
        updated = transition_case(
            case=case, new_status=Case.Status.PENDING_REVIEW, performed_by=admin
        )
        assert updated.status == Case.Status.PENDING_REVIEW

    def test_valid_transition_pending_review_to_in_review(self):
        admin = AdminUserFactory()
        reviewer = ReviewerUserFactory()
        case = CaseFactory(
            created_by=admin, status=Case.Status.PENDING_REVIEW, assigned_to=reviewer
        )
        updated = transition_case(
            case=case, new_status=Case.Status.IN_REVIEW, performed_by=reviewer
        )
        assert updated.status == Case.Status.IN_REVIEW

    def test_valid_transition_in_review_to_approved(self):
        admin = AdminUserFactory()
        reviewer = ReviewerUserFactory()
        case = CaseFactory(
            created_by=admin, status=Case.Status.IN_REVIEW, assigned_to=reviewer
        )
        updated = transition_case(
            case=case, new_status=Case.Status.APPROVED, performed_by=reviewer
        )
        assert updated.status == Case.Status.APPROVED

    def test_valid_transition_in_review_to_rejected(self):
        admin = AdminUserFactory()
        reviewer = ReviewerUserFactory()
        case = CaseFactory(
            created_by=admin, status=Case.Status.IN_REVIEW, assigned_to=reviewer
        )
        updated = transition_case(
            case=case, new_status=Case.Status.REJECTED, performed_by=reviewer
        )
        assert updated.status == Case.Status.REJECTED

    def test_valid_transition_approved_to_closed(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin, status=Case.Status.APPROVED)
        updated = transition_case(
            case=case, new_status=Case.Status.CLOSED, performed_by=admin
        )
        assert updated.status == Case.Status.CLOSED

    def test_valid_transition_rejected_to_closed(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin, status=Case.Status.REJECTED)
        updated = transition_case(
            case=case, new_status=Case.Status.CLOSED, performed_by=admin
        )
        assert updated.status == Case.Status.CLOSED

    def test_invalid_transition_draft_to_approved(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin, status=Case.Status.DRAFT)
        with pytest.raises(ValidationError):
            transition_case(
                case=case, new_status=Case.Status.APPROVED, performed_by=admin
            )

    def test_invalid_transition_draft_to_in_review(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin, status=Case.Status.DRAFT)
        with pytest.raises(ValidationError):
            transition_case(
                case=case, new_status=Case.Status.IN_REVIEW, performed_by=admin
            )

    def test_invalid_transition_pending_to_approved(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin, status=Case.Status.PENDING_REVIEW)
        with pytest.raises(ValidationError):
            transition_case(
                case=case, new_status=Case.Status.APPROVED, performed_by=admin
            )

    def test_invalid_transition_closed_to_anything(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin, status=Case.Status.CLOSED)
        with pytest.raises(ValidationError):
            transition_case(case=case, new_status=Case.Status.DRAFT, performed_by=admin)

    def test_cannot_transition_to_in_review_without_assignment(self):
        admin = AdminUserFactory()
        case = CaseFactory(
            created_by=admin, status=Case.Status.PENDING_REVIEW, assigned_to=None
        )
        with pytest.raises(ValidationError, match="assigned"):
            transition_case(
                case=case, new_status=Case.Status.IN_REVIEW, performed_by=admin
            )

    def test_reviewer_can_only_review_own_cases(self):
        admin = AdminUserFactory()
        reviewer1 = ReviewerUserFactory()
        reviewer2 = ReviewerUserFactory()
        case = CaseFactory(
            created_by=admin,
            status=Case.Status.PENDING_REVIEW,
            assigned_to=reviewer1,
        )
        with pytest.raises(PermissionDenied):
            transition_case(
                case=case, new_status=Case.Status.IN_REVIEW, performed_by=reviewer2
            )

    def test_transition_creates_audit_log(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin, status=Case.Status.DRAFT)
        transition_case(
            case=case, new_status=Case.Status.PENDING_REVIEW, performed_by=admin
        )
        log = AuditLog.objects.filter(case=case, action=AuditLog.Action.STATUS_CHANGE)
        assert log.exists()
        details = log.first().details
        assert details["old_status"] == Case.Status.DRAFT
        assert details["new_status"] == Case.Status.PENDING_REVIEW

    def test_transition_increments_version(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin, status=Case.Status.DRAFT)
        original_version = case.version
        updated = transition_case(
            case=case, new_status=Case.Status.PENDING_REVIEW, performed_by=admin
        )
        assert updated.version == original_version + 1

    def test_invalid_status_value_raises_error(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin, status=Case.Status.DRAFT)
        with pytest.raises(ValidationError, match="Invalid status"):
            transition_case(
                case=case, new_status="nonexistent_status", performed_by=admin
            )


@pytest.mark.django_db
class TestAddComment:
    """Comment creation with audit logging."""

    def test_add_public_comment(self):
        user = OperatorUserFactory()
        case = CaseFactory(created_by=user)
        comment = add_comment(case=case, author=user, content="Test comment")
        assert comment.content == "Test comment"
        assert comment.is_internal is False

    def test_add_internal_comment(self):
        user = AdminUserFactory()
        case = CaseFactory(created_by=user)
        comment = add_comment(
            case=case, author=user, content="Internal note", is_internal=True
        )
        assert comment.is_internal is True

    def test_comment_creates_audit_log(self):
        user = OperatorUserFactory()
        case = CaseFactory(created_by=user)
        comment = add_comment(case=case, author=user, content="Audited comment")
        log = AuditLog.objects.filter(case=case, action=AuditLog.Action.COMMENT_ADDED)
        assert log.exists()
        assert log.first().details["comment_id"] == str(comment.id)


@pytest.mark.django_db
class TestAuditLogImmutability:
    """Audit logs must be immutable."""

    def test_audit_log_cannot_be_updated(self):
        user = OperatorUserFactory()
        case = create_case(user=user, title="Test")
        log = AuditLog.objects.filter(case=case).first()
        log.details = {"tampered": True}
        with pytest.raises(ValueError, match="immutable"):
            log.save()

    def test_audit_log_cannot_be_deleted(self):
        user = OperatorUserFactory()
        case = create_case(user=user, title="Test")
        log = AuditLog.objects.filter(case=case).first()
        with pytest.raises(ValueError, match="immutable"):
            log.delete()
