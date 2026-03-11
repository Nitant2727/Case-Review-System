# DESIGN.md - Architecture & Trade-offs

## Overview

This document explains the key architectural decisions, trade-offs, and production considerations for the Case Review Workflow System.

---

## 1. Where Workflow Logic Lives and Why

**Decision**: All workflow logic is centralised in `cases/services.py` (the service layer).

**Why**:
- **Separation of concerns**: Views handle HTTP request/response parsing; services handle business rules. This keeps views thin and focused on serialization and routing.
- **Testability**: Service functions can be tested in isolation with unit tests, without needing to go through the HTTP layer. This is critical for testing complex state machine rules.
- **Reusability**: The same service functions can be called from management commands, admin actions, Celery tasks, or other internal code paths without duplicating validation logic.
- **Single source of truth**: Having one place for "can this transition happen?" prevents the rules from drifting between views, serializers, and model methods.

**What lives where**:
- `models.py`: Data shape, allowed transition map (`ALLOWED_TRANSITIONS`), and the `can_transition_to()` predicate.
- `services.py`: Orchestration — permission checks, transition validation, audit log creation, and notification dispatch, all wrapped in `transaction.atomic()`.
- `views.py`: HTTP interface — request parsing, serializer validation, calling services, and returning responses.
- `permissions.py`: DRF permission classes for endpoint-level access control.

**Trade-off**: This adds an extra layer compared to putting logic directly in views or serializers. For a small project this is more code, but it pays off immediately once you need to call the same logic from multiple entry points or write focused tests.

---

## 2. How Permissions Are Enforced

Permissions are enforced at **two levels**:

### Level 1: DRF Permission Classes (endpoint-level)

Custom permission classes in `cases/permissions.py` gate access at the view layer:

- `CanCreateCase`: Only `Admin` and `Operator` roles can `POST /cases/`.
- `CanAssignCase`: Only `Admin` can `POST /cases/{id}/assign/`.
- `IsAuthenticated`: All other endpoints require authentication.

These run before the view body executes, providing a fast rejection path.

### Level 2: Service Layer (business-rule-level)

The service functions perform finer-grained checks:

- `create_case()`: Verifies the user's role before creating.
- `assign_case()`: Checks that the performer is Admin and the assignee is a Reviewer.
- `transition_case()`: Checks that:
  - The transition is valid per the state machine.
  - The case is assigned before moving to `in_review`.
  - A Reviewer is only acting on cases assigned to them.

**Why two levels?** DRF permissions give fast 403 responses and are self-documenting in the view layer. Service-layer checks handle rules that depend on the specific data (e.g., "is this case assigned to *this* reviewer?"). Both layers are needed because permissions classes alone cannot express all business rules.

### Role Abstraction

Roles are implemented as a `TextChoices` field on a custom `AbstractUser` subclass. This gives us:
- Database-level constraint on valid role values.
- Easy `is_admin`, `is_reviewer`, `is_operator` properties.
- Simple permission class checks against `request.user.role`.

**Trade-off vs. Django Groups/Permissions**: For three well-defined roles, a simple `role` field is clearer and faster to query than the many-to-many `Group` system. If roles proliferate or need fine-grained per-object permissions, switching to `django-guardian` or `django-rules` would be warranted.

---

## 3. How Audit Logs Are Guaranteed

### Atomic Transactions

Every auditable action (case creation, assignment, status change, comment addition) is wrapped in `transaction.atomic()` in the service layer. The audit log is created *inside* the same transaction as the business operation. If either the business operation or the audit log write fails, the entire transaction rolls back.

```python
with transaction.atomic():
    case.status = new_status
    case.save(update_fields=["status", "version", "updated_at"])
    AuditLog.objects.create(
        case=case, action="status_change", performed_by=user, details={...}
    )
```

### Immutability

The `AuditLog` model enforces immutability at the Django level:

- `save()` raises `ValueError` if the record already exists in the database.
- `delete()` raises `ValueError` unconditionally.
- The Django admin disables add/change/delete permissions for audit logs.

**Trade-off**: This is application-level immutability, not database-level. A raw SQL `UPDATE` or `DELETE` could still modify audit logs. For production, you would add:
- Database-level `BEFORE UPDATE` and `BEFORE DELETE` triggers that `RAISE EXCEPTION`.
- A read-only database user for the audit log table.
- Optionally, an append-only table or external audit store (e.g., event stream).

### Why Not Signals?

Django signals (`post_save`, etc.) are tempting for audit logging but have problems:
- They run outside the caller's transaction boundary unless carefully managed.
- They create implicit, hard-to-trace coupling.
- They can be silently skipped by `bulk_create`, `update()`, or raw SQL.

By keeping audit log creation in the service layer alongside the business operation, we maintain explicit control and transactional guarantees.

---

## 4. What Can Go Wrong With Concurrent Updates

### Race Condition: Status Transition

Two users could simultaneously read the same case in `pending_review` and both attempt to transition it. Without protection, both could succeed and create conflicting state.

**Mitigation**: `select_for_update()` in `transition_case()` acquires a row-level lock:

```python
locked_case = Case.objects.select_for_update().get(pk=case.pk)
```

The first transaction locks the row. The second blocks until the first commits, then re-reads the (now-updated) status and correctly rejects the invalid transition.

### Race Condition: Optimistic Concurrency

The `version` field is incremented atomically using `F("version") + 1`:

```python
locked_case.version = F("version") + 1
locked_case.save(update_fields=["status", "version", "updated_at"])
```

This provides a secondary defence: even without `select_for_update`, a client holding a stale version can be rejected by checking `WHERE version = expected_version`.

### What `select_for_update()` Does NOT Protect Against

- **Deadlocks**: If two transactions lock different rows in different orders, PostgreSQL will detect and abort one. This is rare in our use case (single-row operations) but should be monitored.
- **Long-held locks**: If the transaction does expensive work (e.g., sending an email synchronously) while holding the lock, other requests queue up. Our design mitigates this by doing async work (notifications) *outside* the transaction.
- **SQLite limitations**: SQLite uses database-level locking, not row-level. `select_for_update()` is a no-op on SQLite. For concurrent workloads, PostgreSQL is required.

### Assignment Race

Two admins could simultaneously assign the same case to different reviewers. This is less critical (both are valid operations), but the `select_for_update` in `assign_case` is omitted for simplicity since the last write wins and an audit trail records both assignments. In a production system, you might want to add `select_for_update` there too.

---

## 5. How to Scale Notifications and Filtering in Production

### Notifications

**Current approach**: Celery tasks with Redis broker. The `send_notification` task is dispatched *after* the transaction commits (outside the `transaction.atomic()` block). This avoids the "task dispatched but transaction rolls back" problem for most cases.

**Production scaling**:

1. **Separate notification service**: Extract notifications into a dedicated microservice or use a managed service (AWS SES, SendGrid, Twilio) to decouple the review system from delivery infrastructure.

2. **Transactional outbox pattern**: Instead of dispatching Celery tasks directly, write notification intents to an `outbox` table *inside* the transaction. A separate poller/worker reads the outbox and dispatches. This guarantees at-least-once delivery even if Celery/Redis is temporarily down.

3. **Multiple Celery queues**: Separate queues for different notification types (email, Slack, push) with different worker pools and retry policies.

4. **Idempotency**: Assign a unique ID to each notification and deduplicate on the consumer side to handle retries safely.

5. **Rate limiting**: Use Celery rate limits or a token bucket to avoid overwhelming downstream notification services.

### Filtering

**Current approach**: `django-filter` with `DjangoFilterBackend`. Filters on `status`, `priority`, `assigned_to`, `created_by`, and `created_at` range. Ordering on `created_at`, `priority`, `status`, `updated_at`.

**Production scaling**:

1. **Database indexes**: Add indexes on commonly filtered columns:
   ```python
   class Meta:
       indexes = [
           models.Index(fields=["status", "priority"]),
           models.Index(fields=["assigned_to", "status"]),
           models.Index(fields=["created_by"]),
           models.Index(fields=["-created_at"]),
       ]
   ```

2. **Full-text search**: For searching case titles and descriptions, integrate PostgreSQL full-text search or Elasticsearch.

3. **Cursor-based pagination**: Replace offset pagination with cursor-based pagination for consistent performance on large datasets. Offset pagination degrades as page numbers increase.

4. **Caching**: Cache frequently-accessed filter combinations with Redis. Use Django's cache framework with cache invalidation on writes.

5. **Read replicas**: Route read-heavy listing queries to PostgreSQL read replicas to reduce load on the primary.

6. **Materialized views**: For complex aggregation queries (e.g., "cases per status per reviewer this week"), use PostgreSQL materialized views refreshed periodically.

---

## 6. Additional Design Decisions

### Service Layer vs. Fat Models

I chose a service layer over Django's "fat models" pattern because:
- Workflow operations span multiple models (Case + AuditLog + Comment).
- They require the `request.user` context, which models shouldn't know about.
- Transaction boundaries are clearer when defined in service functions.

### UUID Primary Keys

All models use UUID primary keys instead of auto-incrementing integers:
- Prevents enumeration attacks (users can't guess `case_id=123`).
- Safe for distributed systems (no sequence contention).
- Trade-off: Slightly larger indexes and joins, but negligible for this scale.

### Celery Eager Mode for Tests

Tests run with `CELERY_TASK_ALWAYS_EAGER=True`, executing tasks synchronously in the test process. This avoids needing a running Redis/Celery worker for tests while still exercising the task code paths.

### API Design

- Used explicit `APIView` classes instead of `ModelViewSet` to maintain fine-grained control over each endpoint's behaviour and permissions.
- Custom action endpoints (`/assign/`, `/transition/`) are separate POST endpoints rather than overloaded PATCH operations, making the API's intent explicit and auditable.
