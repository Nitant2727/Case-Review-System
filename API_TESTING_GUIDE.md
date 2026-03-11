# API Testing Guide: Case Review Workflow

This guide provides step-by-step instructions on how to test the API using all three user roles (**Admin**, **Reviewer**, **Operator**). It includes the exact requests, required payloads, and expected responses for each endpoint.

---

## 1. Setup: Creating the Test Users

Since this API focuses on the core workflow and does not have an open user registration endpoint, you need to create the test users via the Django shell.

Run the following command in your terminal to create a **Reviewer** and an **Operator** (the **Admin** user `admin` / `admin123` is already created by Docker). It will also print their UUIDs so you can use them in your API requests.

```bash
docker compose exec web python manage.py shell -c "
from accounts.models import User
rev, _ = User.objects.get_or_create(username='reviewer', defaults={'email':'rev@example.com', 'role':'reviewer'})
rev.set_password('reviewer123')
rev.save()
op, _ = User.objects.get_or_create(username='operator', defaults={'email':'op@example.com', 'role':'operator'})
op.set_password('operator123')
op.save()
print(f'\n--- TEST USERS CREATED ---')
print(f'Admin: admin / admin123')
print(f'Reviewer UUID: {rev.id} (Credentials: reviewer / reviewer123)')
print(f'Operator UUID: {op.id} (Credentials: operator / operator123)')
"
```

*Note down the `Reviewer UUID` from the output; you will need it for the Assignment endpoint.*

---

## 2. API Endpoints Reference

Base URL: `http://localhost:8000`
Authentication: **Basic Auth**

### 2.1 Create a New Case
**Roles Allowed:** `Admin`, `Operator`
*(If you try this as `Reviewer`, you will get a 403 Forbidden).*

**Request:**
```http
POST /api/cases/
Authorization: Basic b3BlcmF0b3I6b3BlcmF0b3IxMjM=  # operator / operator123
Content-Type: application/json

{
    "title": "Suspicious Activity Report - TX",
    "description": "High volume of transactions from new IP address.",
    "priority": "high"
}
```

**Response (201 Created):**
```json
{
    "case_id": "a1b2c3d4-e5f6-7890-abcd-1234567890ab",
    "title": "Suspicious Activity Report - TX",
    "description": "High volume of transactions from new IP address.",
    "priority": "high",
    "status": "draft",
    "created_by": {
        "id": "operator-uuid",
        "username": "operator",
        "email": "op@example.com",
        "role": "operator"
    },
    "assigned_to": null,
    "created_at": "2024-03-11T12:00:00Z",
    "updated_at": "2024-03-11T12:00:00Z",
    "version": 1
}
```
*Note down the `case_id` for the following requests.*

---

### 2.2 List Cases
**Roles Allowed:** All (`Admin`, `Reviewer`, `Operator`)

**Request:**
```http
GET /api/cases/?status=draft&priority=high&ordering=-created_at
Authorization: Basic YWRtaW46YWRtaW4xMjM=  # admin / admin123
```

**Response (200 OK):**
```json
{
    "count": 1,
    "page": 1,
    "page_size": 20,
    "results": [
        {
            "case_id": "a1b2c3d4-e5f6-7890-abcd-1234567890ab",
            "title": "Suspicious Activity Report - TX",
            "status": "draft",
            "...": "..."
        }
    ]
}
```

---

### 2.3 Get Specific Case
**Roles Allowed:** All

**Request:**
```http
GET /api/cases/{case_id}/
Authorization: Basic cmV2aWV3ZXI6cmV2aWV3ZXIxMjM=  # reviewer / reviewer123
```

**Response (200 OK):**
*(Returns the same JSON object as Create Case).*

---

### 2.4 Update Case Fields
**Roles Allowed:** All (must be authenticated)

**Request:**
```http
PATCH /api/cases/{case_id}/
Authorization: Basic b3BlcmF0b3I6b3BlcmF0b3IxMjM=  # operator / operator123
Content-Type: application/json

{
    "priority": "critical"
}
```

**Response (200 OK):**
```json
{
    "case_id": "a1b2c3d4-...",
    "priority": "critical",
    "version": 1,
    "...": "..."
}
```
*(Notice the `priority` is updated, but `version` only increments on status transitions).*

---

### 2.5 Assign Case to Reviewer
**Roles Allowed:** `Admin` ONLY
*(If you try this as `Operator` or `Reviewer`, you will get a 403 Forbidden).*

**Request:**
```http
POST /api/cases/{case_id}/assign/
Authorization: Basic YWRtaW46YWRtaW4xMjM=  # admin / admin123
Content-Type: application/json

{
    "assigned_to": "<PASTE_REVIEWER_UUID_HERE>"
}
```

**Response (200 OK):**
```json
{
    "case_id": "a1b2c3d4-...",
    "assigned_to": {
        "id": "<reviewer-uuid>",
        "username": "reviewer",
        "email": "rev@example.com",
        "role": "reviewer"
    },
    "...": "..."
}
```

---

### 2.6 Transition Case Status
**Roles Allowed:** All, but strictly validated.
*Rules: Must follow strict state machine. Reviewer can only transition cases assigned to them. Cannot move to `in_review` if unassigned.*

#### Step 1: Draft -> Pending Review (Done by Admin or Operator)
**Request:**
```http
POST /api/cases/{case_id}/transition/
Authorization: Basic YWRtaW46YWRtaW4xMjM=  # admin / admin123
Content-Type: application/json

{
    "status": "pending_review"
}
```

#### Step 2: Pending Review -> In Review (Done by the Assigned Reviewer)
**Request:**
```http
POST /api/cases/{case_id}/transition/
Authorization: Basic cmV2aWV3ZXI6cmV2aWV3ZXIxMjM=  # reviewer / reviewer123
Content-Type: application/json

{
    "status": "in_review"
}
```

**Response (200 OK):**
```json
{
    "case_id": "a1b2c3d4-...",
    "status": "in_review",
    "version": 3,
    "...": "..."
}
```
*(Notice the `version` has incremented for concurrency control).*

---

### 2.7 Add Comment
**Roles Allowed:** All

**Request (Internal Comment - Admin/Reviewer):**
```http
POST /api/cases/{case_id}/comments/
Authorization: Basic cmV2aWV3ZXI6cmV2aWV3ZXIxMjM=  # reviewer / reviewer123
Content-Type: application/json

{
    "content": "This IP is a known proxy. Suggest rejecting.",
    "is_internal": true
}
```

**Request (Public Comment - Operator):**
```http
POST /api/cases/{case_id}/comments/
Authorization: Basic b3BlcmF0b3I6b3BlcmF0b3IxMjM=  # operator / operator123
Content-Type: application/json

{
    "content": "Customer called and provided verification documents.",
    "is_internal": false
}
```

**Response (201 Created):**
```json
{
    "id": "c1d2e3f4-...",
    "case": "a1b2c3d4-...",
    "author": {
        "id": "reviewer-uuid",
        "username": "reviewer",
        "role": "reviewer"
    },
    "content": "This IP is a known proxy. Suggest rejecting.",
    "is_internal": true,
    "created_at": "2024-03-11T12:05:00Z"
}
```

---

### 2.8 List Comments (Visibility Rules)
**Roles Allowed:** All, but `Operator` will NOT see `is_internal: true` comments.

**Request:**
```http
GET /api/cases/{case_id}/comments/
Authorization: Basic b3BlcmF0b3I6b3BlcmF0b3IxMjM=  # operator / operator123
```

**Response (200 OK) for Operator:**
*(Will only show the 1 public comment, hiding the internal proxy note).*
```json
[
    {
        "id": "...",
        "content": "Customer called and provided verification documents.",
        "is_internal": false,
        "...": "..."
    }
]
```

If you make the exact same request as **Admin** or **Reviewer**, the response will contain **both** comments.

---

### 2.9 List Audit Logs
**Roles Allowed:** All

**Request:**
```http
GET /api/cases/{case_id}/audit-logs/
Authorization: Basic YWRtaW46YWRtaW4xMjM=  # admin / admin123
```

**Response (200 OK):**
*(Returns an immutable history of everything that happened to the case).*
```json
[
    {
        "id": "log-uuid-5",
        "action": "comment_added",
        "performed_by": {"username": "operator", "role": "operator", "...": "..."},
        "details": {"comment_id": "...", "is_internal": false},
        "created_at": "2024-03-11T12:06:00Z"
    },
    {
        "id": "log-uuid-4",
        "action": "comment_added",
        "performed_by": {"username": "reviewer", "role": "reviewer", "...": "..."},
        "details": {"comment_id": "...", "is_internal": true},
        "created_at": "2024-03-11T12:05:00Z"
    },
    {
        "id": "log-uuid-3",
        "action": "status_change",
        "performed_by": {"username": "reviewer", "role": "reviewer", "...": "..."},
        "details": {"old_status": "pending_review", "new_status": "in_review"},
        "created_at": "2024-03-11T12:04:00Z"
    },
    {
        "id": "log-uuid-2",
        "action": "status_change",
        "performed_by": {"username": "admin", "role": "admin", "...": "..."},
        "details": {"old_status": "draft", "new_status": "pending_review"},
        "created_at": "2024-03-11T12:03:00Z"
    },
    {
        "id": "log-uuid-1",
        "action": "assignment",
        "performed_by": {"username": "admin", "role": "admin", "...": "..."},
        "details": {
            "old_assigned_to": null,
            "new_assigned_to": "reviewer-uuid",
            "assignee_username": "reviewer"
        },
        "created_at": "2024-03-11T12:02:00Z"
    },
    {
        "id": "log-uuid-0",
        "action": "case_created",
        "performed_by": {"username": "operator", "role": "operator", "...": "..."},
        "details": {"title": "Suspicious Activity Report - TX", "priority": "high"},
        "created_at": "2024-03-11T12:00:00Z"
    }
]
```