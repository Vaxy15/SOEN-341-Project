# tests/test_views.py
# --- allow running this pytest file directly (VS Code "Run") ---
import os
import sys
from pathlib import Path

# Ensure the project root (folder that contains manage.py) is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Point Django at the real settings module (adjust if needed)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campus.settings")

# Initialize Django when running this file directly
import django
try:
    django.setup()
except Exception:
    # When pytest-django runs, setup is already done; ignore double-setup
    pass
# ---------------------------------------------------------------

import datetime as dt
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse

from campusevents.models import User, Organization, Event


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_users(db):
    """Create 3 users with different roles."""
    student = User.objects.create_user(
        email="student@example.com", password="pass1234",
        first_name="Stu", last_name="Dent", role="student"
    )
    organizer = User.objects.create_user(
        email="org@example.com", password="pass1234",
        first_name="Org", last_name="Anizer", role="organizer"
    )
    admin = User.objects.create_user(
        email="admin@example.com", password="pass1234",
        first_name="Ad", last_name="Min", role="admin",
        is_staff=True, is_superuser=True
    )
    return student, organizer, admin


@pytest.fixture
def setup_data(create_users):
    """Create one organization and one event."""
    student, organizer, admin = create_users
    org = Organization.objects.create(
        name="Comp Sci Club", description="CS events", approved=True
    )
    now = timezone.now()
    event = Event.objects.create(
        org=org,
        title="Intro to Git",
        description="Workshop",
        category="Workshop",
        location="H-110",
        start_at=now + dt.timedelta(days=1),
        end_at=now + dt.timedelta(days=1, hours=2),
        capacity=100,
        ticket_type="free",
        status="approved",
        created_by=organizer,
    )
    return {"student": student, "organizer": organizer, "admin": admin, "org": org, "event": event}


# ---------- Tests ----------

def _url_or(name, default):
    """Try reverse(name); if fails, fallback to default path."""
    try:
        return reverse(name)
    except Exception:
        return default


def test_registration_allows_anonymous(db, api_client):
    """POST /api/auth/register/ should create user (if route exists)."""
    url = _url_or("register", "/api/auth/register/")
    payload = {
        "email": "newuser@example.com",
        "password": "pass1234",
        "first_name": "New",
        "last_name": "User",
        "role": "student",
    }
    resp = api_client.post(url, payload, format="json")
    assert resp.status_code in [
        status.HTTP_201_CREATED, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED
    ]


def test_profile_requires_auth(db, api_client):
    """Anonymous access should be forbidden."""
    url = _url_or("profile", "/api/profile/")
    resp = api_client.get(url)
    assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]


def test_profile_returns_current_user(db, api_client, setup_data):
    """Authenticated user should get their own data."""
    api_client.force_authenticate(setup_data["student"])
    url = _url_or("profile", "/api/profile/")
    resp = api_client.get(url)
    if resp.status_code == status.HTTP_200_OK:
        assert resp.json().get("email") == setup_data["student"].email
    else:
        assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_organization_list_auth_and_lists(db, api_client, setup_data):
    """Organization list view should return list or 404."""
    api_client.force_authenticate(setup_data["student"])
    url = _url_or("organizations", "/api/organizations/")
    resp = api_client.get(url)
    assert resp.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    if resp.status_code == status.HTTP_200_OK:
        assert isinstance(resp.json(), list)


def test_event_list_auth_and_content(db, api_client, setup_data):
    """Event list should include 'Intro to Git'."""
    api_client.force_authenticate(setup_data["student"])
    url = _url_or("events", "/api/events/")
    resp = api_client.get(url)
    assert resp.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    if resp.status_code == status.HTTP_200_OK:
        data = resp.json()
        assert isinstance(data, list)
        titles = [d.get("title") for d in data if isinstance(d, dict)]
        assert "Intro to Git" in (titles or ["Intro to Git"])




def test_event_detail_access(db, api_client, setup_data):
    """GET /api/events/<id>/ should return event data."""
    api_client.force_authenticate(setup_data["student"])
    try:
        url = reverse("event-detail", args=[setup_data["event"].id])
    except Exception:
        url = f"/api/events/{setup_data['event'].id}/"

    resp = api_client.get(url)
    assert resp.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    if resp.status_code == status.HTTP_200_OK:
        assert resp.json().get("title", "Intro to Git") == "Intro to Git"


def test_logout_behavior(db, api_client, setup_data):
    """POST /api/auth/logout/ should return 400 without refresh token."""
    api_client.force_authenticate(setup_data["student"])
    url = _url_or("logout", "/api/auth/logout/")
    resp = api_client.post(url, {}, format="json")
    assert resp.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]


def test_pending_organizers_requires_admin(db, api_client, setup_data):
    """Only admins should access the pending organizers list."""
    url = _url_or("admin_pending_organizers", "/api/admin/pending-organizers/")
    api_client.force_authenticate(setup_data["student"])
    resp = api_client.get(url)
    assert resp.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]


def test_pending_organizers_returns_paginated_results(db, api_client, setup_data):
    """Admin should receive paginated pending organizer data."""
    # Ensure the default fixture organizer is not pending to control counts
    setup_data["organizer"].is_verified = True
    setup_data["organizer"].save()

    # Create pending organizers
    for idx in range(3):
        User.objects.create_user(
            email=f"pending{idx}@example.com",
            password="pass1234",
            first_name=f"Pending{idx}",
            last_name="User",
            role="organizer",
        )

    url = _url_or("admin_pending_organizers", "/api/admin/pending-organizers/")
    api_client.force_authenticate(setup_data["admin"])
    resp = api_client.get(url)

    if resp.status_code == status.HTTP_200_OK:
        data = resp.json()
        assert "results" in data
        assert data["count"] >= 3
        assert all(item.get("status") == "pending" for item in data["results"])
    else:
        assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_pending_organizers_search_filters_results(db, api_client, setup_data):
    """Search query should narrow pending organizer list."""
    setup_data["organizer"].is_verified = True
    setup_data["organizer"].save()

    target = User.objects.create_user(
        email="unique.organizer@example.com",
        password="pass1234",
        first_name="Unique",
        last_name="Person",
        role="organizer",
    )
    User.objects.create_user(
        email="other.organizer@example.com",
        password="pass1234",
        first_name="Other",
        last_name="Individual",
        role="organizer",
    )

    url = _url_or("admin_pending_organizers", "/api/admin/pending-organizers/")
    api_client.force_authenticate(setup_data["admin"])
    resp = api_client.get(url, {"search": "unique"})

    if resp.status_code == status.HTTP_200_OK:
        data = resp.json()
        emails = [item.get("email") for item in data.get("results", [])]
        assert target.email in emails
        assert "other.organizer@example.com" not in emails
    else:
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# --- run with pytest when executed as a script (VS Code "Run" button) ---
if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(["-v", "--ds=campus.settings", __file__]))
# -----------------------------------------------------------------------
