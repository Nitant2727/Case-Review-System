"""
Test factories for creating test data.
"""

import factory
from django.contrib.auth import get_user_model

from cases.models import AuditLog, Case, Comment

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    role = User.Role.OPERATOR

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """Save again after set_password so the hashed password is persisted."""
        if create:
            instance.save()


class AdminUserFactory(UserFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    role = User.Role.ADMIN
    username = factory.Sequence(lambda n: f"admin_{n}")


class ReviewerUserFactory(UserFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    role = User.Role.REVIEWER
    username = factory.Sequence(lambda n: f"reviewer_{n}")


class OperatorUserFactory(UserFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    role = User.Role.OPERATOR
    username = factory.Sequence(lambda n: f"operator_{n}")


class CaseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Case

    title = factory.Sequence(lambda n: f"Test Case {n}")
    description = factory.Faker("paragraph")
    priority = Case.Priority.MEDIUM
    status = Case.Status.DRAFT
    created_by = factory.SubFactory(OperatorUserFactory)


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    case = factory.SubFactory(CaseFactory)
    author = factory.SubFactory(UserFactory)
    content = factory.Faker("sentence")
    is_internal = False
