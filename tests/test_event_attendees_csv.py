# tests/test_event_attendees_csv.py

from django.urls import reverse
from rest_framework.test import APITestCase, APIClient

from campusevents.models import User, Organization, Event, Ticket


class EventAttendeesCSVTests(APITestCase):
    """Test suite for the 'Export event attendees (CSV)' user story."""

    def setUp(self):
        # Create admin, organizer, students
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

        self.other_organizer = User.objects.create_user(
            email="other_org@example.com",
            password="pw",
            first_name="Other",
            last_name="Organizer",
            role=User.ROLE_ORGANIZER,
            is_verified=True,
        )

        self.student1 = User.objects.create_user(
            email="student1@example.com",
            password="pw",
            first_name="Alice",
            last_name="Student",
            role=User.ROLE_STUDENT,
            student_id="12345678",
            phone_number="555-1234",
        )

        self.student2 = User.objects.create_user(
            email="student2@example.com",
            password="pw",
            first_name="Bob",
            last_name="Student",
            role=User.ROLE_STUDENT,
            student_id="87654321",
        )

        self.organization = Organization.objects.create(name="TestOrg")

        # Event created by org_user
        self.event = Event.objects.create(
            org=self.organization,
            title="Test Event",
            description="Test event description",
            location="Room 101",
            start_at="2025-10-10T10:00:00Z",
            end_at="2025-10-10T12:00:00Z",
            capacity=100,
            created_by=self.org_user,
            status=Event.APPROVED,
        )

        # Event created by another organizer
        self.other_event = Event.objects.create(
            org=self.organization,
            title="Other Event",
            description="Another event",
            location="Room 202",
            start_at="2025-11-15T14:00:00Z",
            end_at="2025-11-15T16:00:00Z",
            capacity=50,
            created_by=self.other_organizer,
            status=Event.APPROVED,
        )

        # Tickets for the main event
        self.ticket1 = Ticket.objects.create(
            event=self.event,
            user=self.student1,
            status="issued"
        )

        self.ticket2 = Ticket.objects.create(
            event=self.event,
            user=self.student2,
            status="used"
        )

        self.client = APIClient()

    # ------------------------------------------------------------
    #                      ACCESS TESTS
    # ------------------------------------------------------------

    def test_admin_can_download_csv(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])

        content = response.content.decode("utf-8")
        self.assertIn("student1@example.com", content)
        self.assertIn("student2@example.com", content)

    def test_event_creator_can_download_csv(self):
        self.client.force_authenticate(user=self.org_user)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        self.assertIn("Alice", content)
        self.assertIn("Bob", content)

    def test_other_organizer_cannot_download_csv(self):
        self.client.force_authenticate(user=self.other_organizer)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.data)

    def test_student_cannot_download_csv(self):
        self.client.force_authenticate(user=self.student1)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_download_csv(self):
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})

        response = self.client.get(url)

        self.assertIn(response.status_code, [401, 403])

    # ------------------------------------------------------------
    #                    CONTENT / FORMAT TESTS
    # ------------------------------------------------------------

    def test_csv_contains_correct_headers(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})

        response = self.client.get(url)
        content = response.content.decode("utf-8")

        headers = [
            "ticket_id", "ticket_status", "user_email",
            "first_name", "last_name", "student_id",
            "phone_number", "issued_at",
        ]

        for h in headers:
            self.assertIn(h, content)

    def test_csv_contains_correct_data(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})

        response = self.client.get(url)
        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")

        # header + 2 tickets
        self.assertEqual(len(lines), 3)

        self.assertIn("Alice", content)
        self.assertIn("Bob", content)
        self.assertIn("12345678", content)
        self.assertIn("87654321", content)
        self.assertIn("555-1234", content)

    # ------------------------------------------------------------
    #                        FILTER TESTS
    # ------------------------------------------------------------

    def test_csv_filter_by_status_issued(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})

        response = self.client.get(url, {"status": "issued"})
        content = response.content.decode("utf-8")

        self.assertIn("student1@example.com", content)
        self.assertNotIn("student2@example.com", content)

    def test_csv_filter_by_status_used(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})

        response = self.client.get(url, {"status": "used"})
        content = response.content.decode("utf-8")

        self.assertIn("student2@example.com", content)
        self.assertNotIn("student1@example.com", content)

    # ------------------------------------------------------------
    #                       MISC TESTS
    # ------------------------------------------------------------

    def test_csv_filename_contains_event_id(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})

        response = self.client.get(url)
        content_disposition = response["Content-Disposition"]

        self.assertIn(f"attendees_event_{self.event.id}.csv", content_disposition)

    def test_csv_for_event_with_no_attendees(self):
        empty_event = Event.objects.create(
            org=self.organization,
            title="Empty Event",
            description="No attendees",
            location="Room 303",
            start_at="2025-12-01T10:00:00Z",
            end_at="2025-12-01T12:00:00Z",
            capacity=50,
            created_by=self.org_user,
            status=Event.APPROVED,
        )

        self.client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": empty_event.id})

        response = self.client.get(url)
        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")

        self.assertEqual(len(lines), 1)  # only header
        self.assertIn("ticket_id", lines[0])

    def test_csv_for_nonexistent_event_returns_404(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": 99999})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
