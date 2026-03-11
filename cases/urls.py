from django.urls import path

from . import views

app_name = "cases"

urlpatterns = [
    path("cases/", views.CaseListCreateView.as_view(), name="case-list-create"),
    path("cases/<uuid:pk>/", views.CaseDetailView.as_view(), name="case-detail"),
    path("cases/<uuid:pk>/assign/", views.CaseAssignView.as_view(), name="case-assign"),
    path(
        "cases/<uuid:pk>/transition/",
        views.CaseTransitionView.as_view(),
        name="case-transition",
    ),
    path(
        "cases/<uuid:pk>/comments/",
        views.CommentListCreateView.as_view(),
        name="case-comments",
    ),
    path(
        "cases/<uuid:pk>/audit-logs/",
        views.AuditLogListView.as_view(),
        name="case-audit-logs",
    ),
]
