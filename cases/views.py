"""
API views for Case workflow system.
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User

from .filters import CaseFilter
from .models import AuditLog, Case, Comment
from .permissions import CanAssignCase, CanCreateCase
from .serializers import (
    AuditLogSerializer,
    AssignCaseSerializer,
    CaseCreateSerializer,
    CaseSerializer,
    CaseUpdateSerializer,
    CommentCreateSerializer,
    CommentSerializer,
    TransitionSerializer,
)
from .services import add_comment, assign_case, create_case, transition_case


class CaseListCreateView(APIView):
    """
    GET  /cases/  – list cases with filtering & sorting
    POST /cases/  – create a new case
    """

    permission_classes = [CanCreateCase]

    @extend_schema(
        operation_id="cases_list",
        parameters=[
            OpenApiParameter("status", str, description="Filter by status"),
            OpenApiParameter("priority", str, description="Filter by priority"),
            OpenApiParameter(
                "assigned_to", str, description="Filter by assigned reviewer UUID"
            ),
            OpenApiParameter("created_by", str, description="Filter by creator UUID"),
            OpenApiParameter(
                "ordering",
                str,
                description="Order by field (e.g. -created_at, priority)",
            ),
            OpenApiParameter("page", int, description="Page number"),
            OpenApiParameter("page_size", int, description="Page size"),
        ],
        responses={200: CaseSerializer(many=True)},
    )
    def get(self, request):
        queryset = Case.objects.select_related("created_by", "assigned_to").all()

        # Apply filters
        filterset = CaseFilter(request.query_params, queryset=queryset)
        if not filterset.is_valid():
            return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)
        queryset = filterset.qs

        # Ordering
        ordering = request.query_params.get("ordering", "-created_at")
        allowed_ordering = [
            "created_at",
            "-created_at",
            "priority",
            "-priority",
            "status",
            "-status",
            "updated_at",
            "-updated_at",
        ]
        if ordering in allowed_ordering:
            queryset = queryset.order_by(ordering)

        # Simple pagination
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        start = (page - 1) * page_size
        end = start + page_size
        total = queryset.count()

        serializer = CaseSerializer(queryset[start:end], many=True)
        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "results": serializer.data,
            }
        )

    @extend_schema(
        operation_id="cases_create",
        request=CaseCreateSerializer,
        responses={201: CaseSerializer},
    )
    def post(self, request):
        serializer = CaseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = create_case(user=request.user, **serializer.validated_data)
        return Response(CaseSerializer(case).data, status=status.HTTP_201_CREATED)


class CaseDetailView(APIView):
    """
    GET   /cases/{id}/  – retrieve case
    PATCH /cases/{id}/  – update case fields (title, description, priority)
    """

    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Case.objects.select_related("created_by", "assigned_to"), pk=pk
        )

    @extend_schema(
        operation_id="cases_retrieve",
        responses={200: CaseSerializer},
    )
    def get(self, request, pk):
        case = self.get_object(pk)
        return Response(CaseSerializer(case).data)

    @extend_schema(
        operation_id="cases_partial_update",
        request=CaseUpdateSerializer,
        responses={200: CaseSerializer},
    )
    def patch(self, request, pk):
        case = self.get_object(pk)
        serializer = CaseUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        update_fields = []
        for field, value in serializer.validated_data.items():
            setattr(case, field, value)
            update_fields.append(field)

        if update_fields:
            update_fields.append("updated_at")
            case.save(update_fields=update_fields)

        return Response(CaseSerializer(case).data)


class CaseAssignView(APIView):
    """POST /cases/{id}/assign/ – assign case to a reviewer."""

    permission_classes = [CanAssignCase]

    @extend_schema(
        operation_id="cases_assign",
        request=AssignCaseSerializer,
        responses={200: CaseSerializer},
    )
    def post(self, request, pk):
        case = get_object_or_404(Case, pk=pk)
        serializer = AssignCaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignee = User.objects.get(pk=serializer.validated_data["assigned_to"])
        case = assign_case(case=case, assignee=assignee, performed_by=request.user)
        return Response(CaseSerializer(case).data)


class CaseTransitionView(APIView):
    """POST /cases/{id}/transition/ – transition case status."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="cases_transition",
        request=TransitionSerializer,
        responses={200: CaseSerializer},
    )
    def post(self, request, pk):
        case = get_object_or_404(Case, pk=pk)
        serializer = TransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        case = transition_case(
            case=case,
            new_status=serializer.validated_data["status"],
            performed_by=request.user,
        )
        return Response(CaseSerializer(case).data)


class CommentListCreateView(APIView):
    """
    GET  /cases/{id}/comments/  – list comments (filtered by visibility)
    POST /cases/{id}/comments/  – add comment
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="cases_comments_list",
        responses={200: CommentSerializer(many=True)},
    )
    def get(self, request, pk):
        case = get_object_or_404(Case, pk=pk)
        comments = Comment.objects.select_related("author").filter(case=case)

        # Internal comments visible only to Admin and Reviewer
        if request.user.role not in (User.Role.ADMIN, User.Role.REVIEWER):
            comments = comments.filter(is_internal=False)

        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    @extend_schema(
        operation_id="cases_comments_create",
        request=CommentCreateSerializer,
        responses={201: CommentSerializer},
    )
    def post(self, request, pk):
        case = get_object_or_404(Case, pk=pk)
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = add_comment(
            case=case,
            author=request.user,
            **serializer.validated_data,
        )
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)


class AuditLogListView(APIView):
    """GET /cases/{id}/audit-logs/ – list audit logs for a case."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="cases_audit_logs_list",
        responses={200: AuditLogSerializer(many=True)},
    )
    def get(self, request, pk):
        case = get_object_or_404(Case, pk=pk)
        logs = AuditLog.objects.select_related("performed_by").filter(case=case)
        serializer = AuditLogSerializer(logs, many=True)
        return Response(serializer.data)
