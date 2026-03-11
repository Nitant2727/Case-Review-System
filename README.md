# Case Review Workflow System

A Django REST API for managing case review workflows with role-based access control, strict status transitions, audit logging, and async notifications.

## Tech Stack

- **Django 6.0** + **Django REST Framework 3.16**
- **PostgreSQL 16** (via Docker; SQLite for local dev)
- **Celery** + **Redis** for async notifications
- **drf-spectacular** for OpenAPI/Swagger docs
- **pytest** + **Factory Boy** for testing

## Quick Start (Docker)

```bash
docker compose up --build
```

This starts all services:
- **Web**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Celery worker**: background task processing

A default admin user is created automatically:
- Username: `admin`
- Password: `admin123`

### API Documentation

- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

## Quick Start (Local)

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Run the development server
python manage.py runserver
```

## Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest -v

# Run with coverage
pytest --cov=cases --cov=accounts -v
```

All 53 tests cover:
- Case creation permissions (Admin/Operator only)
- Case assignment permissions (Admin only, to Reviewers only)
- All valid and invalid status transitions
- Reviewer can only review assigned cases
- Case cannot move to `in_review` without assignment
- Internal comment visibility rules
- Audit log immutability
- Full workflow happy path (end-to-end)
- API filtering and ordering
- Authentication enforcement

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/cases/` | Create a new case |
| GET | `/api/cases/` | List cases (with filtering/sorting) |
| GET | `/api/cases/{id}/` | Retrieve a case |
| PATCH | `/api/cases/{id}/` | Update case fields |
| POST | `/api/cases/{id}/assign/` | Assign case to reviewer |
| POST | `/api/cases/{id}/transition/` | Transition case status |
| POST | `/api/cases/{id}/comments/` | Add comment to case |
| GET | `/api/cases/{id}/comments/` | List case comments |
| GET | `/api/cases/{id}/audit-logs/` | List case audit logs |

### Authentication

All endpoints require authentication. Use session auth or basic auth:

```bash
# Basic auth example
curl -u admin:admin123 http://localhost:8000/api/cases/
```

### Filtering & Sorting

```bash
# Filter by status
GET /api/cases/?status=draft

# Filter by priority
GET /api/cases/?priority=high

# Filter by assigned reviewer
GET /api/cases/?assigned_to=<uuid>

# Filter by creator
GET /api/cases/?created_by=<uuid>

# Filter by date range
GET /api/cases/?created_at_after=2024-01-01&created_at_before=2024-12-31

# Sort results
GET /api/cases/?ordering=-created_at
GET /api/cases/?ordering=priority
```

## User Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Create cases, assign cases, transition status, view all comments |
| **Reviewer** | Review assigned cases, transition status on assigned cases, view internal comments |
| **Operator** | Create cases, add comments, view public comments only |

## Status Transitions

```
draft -> pending_review -> in_review -> approved -> closed
                                    \-> rejected -> closed
```

## Project Structure

```
├── accounts/           # Custom User model with roles
│   ├── models.py       # User model (Admin, Reviewer, Operator)
│   ├── serializers.py   # User serializer
│   └── admin.py        # Django admin config
├── cases/              # Core business logic
│   ├── models.py       # Case, Comment, AuditLog models
│   ├── services.py     # Business logic / service layer
│   ├── views.py        # API views
│   ├── serializers.py  # DRF serializers
│   ├── permissions.py  # Role-based permissions
│   ├── filters.py      # django-filter FilterSets
│   ├── tasks.py        # Celery async tasks
│   ├── urls.py         # URL routing
│   └── tests/          # Comprehensive test suite
├── config/             # Django project configuration
│   ├── settings.py     # Settings with env var support
│   ├── celery.py       # Celery configuration
│   └── urls.py         # Root URL config
├── Dockerfile          # Container image
├── docker-compose.yml  # Full stack orchestration
├── requirements.txt    # Python dependencies
├── DESIGN.md           # Architecture & trade-offs
└── README.md           # This file
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | insecure default | Django secret key |
| `DJANGO_DEBUG` | `True` | Debug mode |
| `DJANGO_ALLOWED_HOSTS` | `*` | Allowed hosts |
| `DB_ENGINE` | `sqlite3` | Database engine |
| `DB_NAME` | `db.sqlite3` | Database name |
| `DB_USER` | `` | Database user |
| `DB_PASSWORD` | `` | Database password |
| `DB_HOST` | `` | Database host |
| `DB_PORT` | `` | Database port |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Celery backend |
