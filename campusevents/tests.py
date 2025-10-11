from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from .models import User, Organization, Event, Ticket


class EventAttendeesCSVTests(APITestCase):
    def setUp(self):
        # create admin, organizer, student
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="pw",
            first_name="Admin",
            last_name="User",
        )
        self.org_user = User.objects.create_user(
            email="org@example.com",
            password="pw",
            first_name="Org",
            last_name="User",
            role=User.ROLE_ORGANIZER,
            is_verified=True,
        )
        self.student = User.objects.create_user(
            email="student@example.com",
            password="pw",
            first_name="Stu",
            last_name="Dent",
        )

        self.organization = Organization.objects.create(name="TestOrg")
        self.event = Event.objects.create(
            org=self.organization,
            title="Test Event",
            description="d",
            location="loc",
            start_at="2025-10-10T10:00:00Z",
            end_at="2025-10-10T12:00:00Z",
            capacity=100,
            created_by=self.org_user,
            status=Event.APPROVED,
        )

        Ticket.objects.create(event=self.event, user=self.student)

    def test_admin_can_download_csv(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv", kwargs={"primary_key": self.event.id})
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        content = resp.content.decode("utf-8")
        self.assertIn("student@example.com", content)
