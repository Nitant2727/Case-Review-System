"""
django-filter FilterSet for Case listing with filtering and ordering.
"""

import django_filters

from .models import Case


class CaseFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Case.Status.choices)
    priority = django_filters.ChoiceFilter(choices=Case.Priority.choices)
    assigned_to = django_filters.UUIDFilter(field_name="assigned_to__id")
    created_by = django_filters.UUIDFilter(field_name="created_by__id")
    created_at_after = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_at_before = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )

    class Meta:
        model = Case
        fields = ["status", "priority", "assigned_to", "created_by"]
