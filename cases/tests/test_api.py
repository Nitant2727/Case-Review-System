"""
Tests for API endpoints – covers permission checks, response codes, and data integrity.
"""

import pytest
from rest_framework.test import APIClient

from cases.models import AuditLog, Case, Comment

from . import (
    AdminUserFactory,
    CaseFactory,
    CommentFactory,
    OperatorUserFactory,
    ReviewerUserFactory,
)


def api_client(user):
    """Return an authenticated API client."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestCaseListCreateAPI:
    """POST /api/cases/ and GET /api/cases/"""

    def test_create_case_as_operator(self):
        user = OperatorUserFactory()
        resp = api_client(user).post(
            "/api/cases/",
            {"title": "New Case", "priority": "high"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["title"] == "New Case"
        assert resp.data["status"] == "draft"

    def test_create_case_as_admin(self):
        user = AdminUserFactory()
        resp = api_client(user).post(
            "/api/cases/",
            {"title": "Admin Case"},
            format="json",
        )
        assert resp.status_code == 201

    def test_create_case_as_reviewer_forbidden(self):
        user = ReviewerUserFactory()
        resp = api_client(user).post(
            "/api/cases/",
            {"title": "Should Fail"},
            format="json",
        )
        assert resp.status_code == 403

    def test_list_cases(self):
        admin = AdminUserFactory()
        CaseFactory.create_batch(3, created_by=admin)
        resp = api_client(admin).get("/api/cases/")
        assert resp.status_code == 200
        assert resp.data["count"] == 3
        assert len(resp.data["results"]) == 3

    def test_list_cases_filter_by_status(self):
        admin = AdminUserFactory()
        CaseFactory(created_by=admin, status=Case.Status.DRAFT)
        CaseFactory(created_by=admin, status=Case.Status.PENDING_REVIEW)
        resp = api_client(admin).get("/api/cases/?status=draft")
        assert resp.status_code == 200
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["status"] == "draft"

    def test_list_cases_filter_by_priority(self):
        admin = AdminUserFactory()
        CaseFactory(created_by=admin, priority=Case.Priority.HIGH)
        CaseFactory(created_by=admin, priority=Case.Priority.LOW)
        resp = api_client(admin).get("/api/cases/?priority=high")
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_list_cases_filter_by_assigned_to(self):
        admin = AdminUserFactory()
        reviewer = ReviewerUserFactory()
        CaseFactory(created_by=admin, assigned_to=reviewer)
        CaseFactory(created_by=admin, assigned_to=None)
        resp = api_client(admin).get(f"/api/cases/?assigned_to={reviewer.id}")
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_list_cases_ordering(self):
        admin = AdminUserFactory()
        CaseFactory(created_by=admin, priority=Case.Priority.LOW)
        CaseFactory(created_by=admin, priority=Case.Priority.HIGH)
        resp = api_client(admin).get("/api/cases/?ordering=priority")
        assert resp.status_code == 200

    def test_unauthenticated_access_denied(self):
        resp = APIClient().get("/api/cases/")
        assert resp.status_code == 403


@pytest.mark.django_db
class TestCaseDetailAPI:
    """GET /api/cases/{id}/ and PATCH /api/cases/{id}/"""

    def test_retrieve_case(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin)
        resp = api_client(admin).get(f"/api/cases/{case.case_id}/")
        assert resp.status_code == 200
        assert resp.data["case_id"] == str(case.case_id)

    def test_update_case_title(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin)
        resp = api_client(admin).patch(
            f"/api/cases/{case.case_id}/",
            {"title": "Updated Title"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["title"] == "Updated Title"

    def test_update_case_priority(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin, priority=Case.Priority.LOW)
        resp = api_client(admin).patch(
            f"/api/cases/{case.case_id}/",
            {"priority": "critical"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["priority"] == "critical"

    def test_retrieve_nonexistent_case_returns_404(self):
        admin = AdminUserFactory()
        resp = api_client(admin).get("/api/cases/00000000-0000-0000-0000-000000000000/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestCaseAssignAPI:
    """POST /api/cases/{id}/assign/"""

    def test_admin_assigns_case(self):
        admin = AdminUserFactory()
        reviewer = ReviewerUserFactory()
        case = CaseFactory(created_by=admin)
        resp = api_client(admin).post(
            f"/api/cases/{case.case_id}/assign/",
            {"assigned_to": str(reviewer.id)},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["assigned_to"]["id"] == str(reviewer.id)

    def test_operator_cannot_assign(self):
        operator = OperatorUserFactory()
        reviewer = ReviewerUserFactory()
        case = CaseFactory(created_by=operator)
        resp = api_client(operator).post(
            f"/api/cases/{case.case_id}/assign/",
            {"assigned_to": str(reviewer.id)},
            format="json",
        )
        assert resp.status_code == 403

    def test_assign_to_non_reviewer_fails(self):
        admin = AdminUserFactory()
        operator = OperatorUserFactory()
        case = CaseFactory(created_by=admin)
        resp = api_client(admin).post(
            f"/api/cases/{case.case_id}/assign/",
            {"assigned_to": str(operator.id)},
            format="json",
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestCaseTransitionAPI:
    """POST /api/cases/{id}/transition/"""

    def test_valid_transition(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin, status=Case.Status.DRAFT)
        resp = api_client(admin).post(
            f"/api/cases/{case.case_id}/transition/",
            {"status": "pending_review"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["status"] == "pending_review"

    def test_invalid_transition_returns_400(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin, status=Case.Status.DRAFT)
        resp = api_client(admin).post(
            f"/api/cases/{case.case_id}/transition/",
            {"status": "approved"},
            format="json",
        )
        assert resp.status_code == 400

    def test_transition_to_in_review_without_assignee_fails(self):
        admin = AdminUserFactory()
        case = CaseFactory(
            created_by=admin, status=Case.Status.PENDING_REVIEW, assigned_to=None
        )
        resp = api_client(admin).post(
            f"/api/cases/{case.case_id}/transition/",
            {"status": "in_review"},
            format="json",
        )
        assert resp.status_code == 400

    def test_full_workflow_happy_path(self):
        """Test the complete lifecycle: draft -> pending_review -> in_review -> approved -> closed"""
        admin = AdminUserFactory()
        reviewer = ReviewerUserFactory()

        # Create
        resp = api_client(admin).post(
            "/api/cases/",
            {"title": "Full Workflow", "priority": "high"},
            format="json",
        )
        assert resp.status_code == 201
        case_id = resp.data["case_id"]

        # Assign
        resp = api_client(admin).post(
            f"/api/cases/{case_id}/assign/",
            {"assigned_to": str(reviewer.id)},
            format="json",
        )
        assert resp.status_code == 200

        # draft -> pending_review
        resp = api_client(admin).post(
            f"/api/cases/{case_id}/transition/",
            {"status": "pending_review"},
            format="json",
        )
        assert resp.status_code == 200

        # pending_review -> in_review (by assigned reviewer)
        resp = api_client(reviewer).post(
            f"/api/cases/{case_id}/transition/",
            {"status": "in_review"},
            format="json",
        )
        assert resp.status_code == 200

        # in_review -> approved (by assigned reviewer)
        resp = api_client(reviewer).post(
            f"/api/cases/{case_id}/transition/",
            {"status": "approved"},
            format="json",
        )
        assert resp.status_code == 200

        # approved -> closed
        resp = api_client(admin).post(
            f"/api/cases/{case_id}/transition/",
            {"status": "closed"},
            format="json",
        )
        assert resp.status_code == 200

        # Verify audit trail
        resp = api_client(admin).get(f"/api/cases/{case_id}/audit-logs/")
        assert resp.status_code == 200
        # case_created + assignment + 4 transitions = 6
        assert len(resp.data) == 6


@pytest.mark.django_db
class TestCommentAPI:
    """POST /api/cases/{id}/comments/ and GET /api/cases/{id}/comments/"""

    def test_add_comment(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin)
        resp = api_client(admin).post(
            f"/api/cases/{case.case_id}/comments/",
            {"content": "A comment"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["content"] == "A comment"

    def test_internal_comment_visibility_admin(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin)
        CommentFactory(case=case, author=admin, content="Public", is_internal=False)
        CommentFactory(case=case, author=admin, content="Internal", is_internal=True)

        resp = api_client(admin).get(f"/api/cases/{case.case_id}/comments/")
        assert resp.status_code == 200
        assert len(resp.data) == 2

    def test_internal_comment_visibility_reviewer(self):
        admin = AdminUserFactory()
        reviewer = ReviewerUserFactory()
        case = CaseFactory(created_by=admin)
        CommentFactory(case=case, author=admin, content="Public", is_internal=False)
        CommentFactory(case=case, author=admin, content="Internal", is_internal=True)

        resp = api_client(reviewer).get(f"/api/cases/{case.case_id}/comments/")
        assert resp.status_code == 200
        assert len(resp.data) == 2  # Reviewer can see internal comments

    def test_internal_comment_hidden_from_operator(self):
        admin = AdminUserFactory()
        operator = OperatorUserFactory()
        case = CaseFactory(created_by=admin)
        CommentFactory(case=case, author=admin, content="Public", is_internal=False)
        CommentFactory(case=case, author=admin, content="Internal", is_internal=True)

        resp = api_client(operator).get(f"/api/cases/{case.case_id}/comments/")
        assert resp.status_code == 200
        assert len(resp.data) == 1  # Operator cannot see internal comments
        assert resp.data[0]["content"] == "Public"


@pytest.mark.django_db
class TestAuditLogAPI:
    """GET /api/cases/{id}/audit-logs/"""

    def test_list_audit_logs(self):
        admin = AdminUserFactory()
        case = CaseFactory(created_by=admin)
        # CaseFactory doesn't go through create_case service, so create one via service
        from cases.services import create_case as svc_create

        case2 = svc_create(user=admin, title="Service Case")
        resp = api_client(admin).get(f"/api/cases/{case2.case_id}/audit-logs/")
        assert resp.status_code == 200
        assert len(resp.data) >= 1
        assert resp.data[0]["action"] == "case_created"
