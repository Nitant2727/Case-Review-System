import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with role-based access control."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        REVIEWER = "reviewer", "Reviewer"
        OPERATOR = "operator", "Operator"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OPERATOR)

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_reviewer(self):
        return self.role == self.Role.REVIEWER

    @property
    def is_operator(self):
        return self.role == self.Role.OPERATOR
