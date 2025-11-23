# tests/test_admin_dashboard_stats.py

from django.urls import reverse
from rest_framework.test import APITestCase, APIClient

from campusevents.models import User, Organization, Event, Ticket


class DashboardOverviewTests(APITestCase):
    """Test suite for the 'Dashboard overview' user story."""

    def setUp(self):
        # Create admin user
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass",
            first_name="Admin",
            last_name="User",
        )

        # Verified organizers
        self.verified_org1 = User.objects.create_user(
            email="verified1@example.com",
            password="pw",
            first_name="Verified",
            last_name="One",
            role=User.ROLE_ORGANIZER,
            is_verified=True,
            is_active=True,
        )
        self.verified_org2 = User.objects.create_user(
            email="verified2@example.com",
            password="pw",
            first_name="Verified",
            last_name="Two",
            role=User.ROLE_ORGANIZER,
            is_verified=True,
            is_active=True,
        )

        # Pending organizers
        self.pending_org1 = User.objects.create_user(
            email="pending1@example.com",
            password="pw",
            first_name="Pending",
            last_name="One",
            role=User.ROLE_ORGANIZER,
            is_verified=False,
            is_active=False,
        )
        self.pending_org2 = User.objects.create_user(
            email="pending2@example.com",
            password="pw",
            first_name="Pending",
            last_name="Two",
            role=User.ROLE_ORGANIZER,
            is_verified=False,
            is_active=False,
        )

        # Students
        self.student1 = User.objects.create_user(
            email="student1@example.com",
            password="pw",
            first_name="Student",
            last_name="One",
            role=User.ROLE_STUDENT,
        )
        self.student2 = User.objects.create_user(
            email="student2@example.com",
            password="pw",
            first_name="Student",
            last_name="Two",
            role=User.ROLE_STUDENT,
        )

        self.organization = Organization.objects.create(name="Test Org")

        # Events with different statuses
        self.approved_event = Event.objects.create(
            org=self.organization,
            title="Approved Event",
            description="Approved",
            location="Room 1",
            start_at="2025-12-01T10:00:00Z",
            end_at="2025-12-01T12:00:00Z",
            capacity=100,
            created_by=self.verified_org1,
            status=Event.APPROVED,
        )

        self.pending_event1 = Event.objects.create(
            org=self.organization,
            title="Pending Event 1",
            description="Pending",
            location="Room 2",
            start_at="2025-12-05T14:00:00Z",
            end_at="2025-12-05T16:00:00Z",
            capacity=50,
            created_by=self.verified_org1,
            status=Event.PENDING,
        )

        self.pending_event2 = Event.objects.create(
            org=self.organization,
            title="Pending Event 2",
            description="Another pending",
            location="Room 3",
            start_at="2025-12-10T10:00:00Z",
            end_at="2025-12-10T12:00:00Z",
            capacity=75,
            created_by=self.verified_org2,
            status=Event.PENDING,
        )

        # Tickets with different statuses
        self.issued_ticket1 = Ticket.objects.create(
            event=self.approved_event,
            user=self.student1,
            status=Ticket.ISSUED,
        )

        self.used_ticket = Ticket.objects.create(
            event=self.approved_event,
            user=self.student2,
            status=Ticket.USED,
        )

        self.client = APIClient()

    # ========== BASIC ACCESS TESTS ==========

    def test_admin_can_access_dashboard_stats(self):
        """Admin can access dashboard stats endpoint."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("totals", response.data)

    def test_non_admin_cannot_access_dashboard_stats(self):
        """Non-admin users cannot access dashboard stats."""
        self.client.force_authenticate(user=self.student1)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.data)

    def test_organizer_cannot_access_dashboard_stats(self):
        """Organizers cannot access dashboard stats."""
        self.client.force_authenticate(user=self.verified_org1)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_access_dashboard(self):
        """Unauthenticated users cannot access dashboard stats."""
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        self.assertIn(response.status_code, [401, 403])

    # ========== TOTALS TESTS ==========

    def test_dashboard_contains_totals_section(self):
        """Dashboard response contains totals section."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        self.assertIn("totals", response.data)
        totals = response.data["totals"]

        self.assertIn("total_users", totals)
        self.assertIn("total_events", totals)
        self.assertIn("tickets_issued_total", totals)
        self.assertIn("tickets_used_total", totals)
        self.assertIn("verified_organizers", totals)
        self.assertIn("pending_organizers", totals)
        self.assertIn("pending_events", totals)

    def test_dashboard_total_users_count(self):
        """Total users count is accurate."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        # 1 admin + 2 verified orgs + 2 pending orgs + 2 students = 7
        self.assertEqual(response.data["totals"]["total_users"], 7)

    def test_dashboard_verified_organizers_count(self):
        """Verified organizers count is accurate."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        self.assertEqual(response.data["totals"]["verified_organizers"], 2)

    def test_dashboard_pending_organizers_count(self):
        """Pending organizers count is accurate."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        self.assertEqual(response.data["totals"]["pending_organizers"], 2)

    def test_dashboard_total_events_count(self):
        """Total events count is accurate."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        # 1 approved + 2 pending
        self.assertEqual(response.data["totals"]["total_events"], 3)

    def test_dashboard_pending_events_count(self):
        """Pending events count is accurate."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        self.assertEqual(response.data["totals"]["pending_events"], 2)

    def test_dashboard_tickets_issued_count(self):
        """Issued tickets count is accurate."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        self.assertEqual(response.data["totals"]["tickets_issued_total"], 1)

    def test_dashboard_tickets_used_count(self):
        """Used tickets count is accurate."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        self.assertEqual(response.data["totals"]["tickets_used_total"], 1)

    # ========== MONTHLY DATA TESTS ==========

    def test_dashboard_contains_events_per_month(self):
        """Dashboard contains events per month data."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        self.assertIn("events_per_month", response.data)
        self.assertIsInstance(response.data["events_per_month"], list)
        self.assertEqual(len(response.data["events_per_month"]), 12)

    def test_dashboard_events_per_month_structure(self):
        """Events per month has correct structure."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)
        events_per_month = response.data["events_per_month"]

        if events_per_month:
            entry = events_per_month[0]
            self.assertIn("month", entry)
            self.assertIn("count", entry)

    def test_dashboard_contains_tickets_per_month(self):
        """Dashboard contains tickets per month data."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        self.assertIn("tickets_per_month", response.data)
        self.assertIsInstance(response.data["tickets_per_month"], list)
        self.assertEqual(len(response.data["tickets_per_month"]), 12)

    def test_dashboard_tickets_per_month_structure(self):
        """Tickets per month has correct structure."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)
        tickets_per_month = response.data["tickets_per_month"]

        if tickets_per_month:
            entry = tickets_per_month[0]
            self.assertIn("month", entry)
            self.assertIn("issued", entry)
            self.assertIn("used", entry)
            self.assertIn("participation_rate", entry)

    # ========== TOP EVENTS TESTS ==========

    def test_dashboard_contains_top_events_by_checkins(self):
        """Dashboard contains top events by check-ins."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        self.assertIn("top_events_by_checkins", response.data)
        self.assertIsInstance(response.data["top_events_by_checkins"], list)

    def test_dashboard_top_events_structure(self):
        """Top events have correct structure."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)
        top_events = response.data["top_events_by_checkins"]

        if top_events:
            event = top_events[0]
            self.assertIn("event_id", event)
            self.assertIn("title", event)
            self.assertIn("used", event)

    def test_dashboard_top_events_limited_to_five(self):
        """Top events list is limited to 5 entries."""
        # Create more events with used tickets
        for i in range(10):
            event = Event.objects.create(
                org=self.organization,
                title=f"Event {i}",
                description="Test",
                location="Room",
                start_at="2025-12-15T10:00:00Z",
                end_at="2025-12-15T12:00:00Z",
                capacity=50,
                created_by=self.verified_org1,
                status=Event.APPROVED,
            )
            Ticket.objects.create(
                event=event,
                user=self.student1,
                status=Ticket.USED,
            )

        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response = self.client.get(url)

        self.assertLessEqual(len(response.data["top_events_by_checkins"]), 5)

    # ========== DYNAMIC UPDATES TESTS ==========

    def test_dashboard_updates_when_new_user_added(self):
        """Dashboard reflects changes when new user is added."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response1 = self.client.get(url)
        initial_count = response1.data["totals"]["total_users"]

        User.objects.create_user(
            email="newuser@example.com",
            password="pw",
            first_name="New",
            last_name="User",
        )

        response2 = self.client.get(url)
        new_count = response2.data["totals"]["total_users"]

        self.assertEqual(new_count, initial_count + 1)

    def test_dashboard_updates_when_organizer_approved(self):
        """Dashboard reflects changes when organizer is approved."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")

        response1 = self.client.get(url)
        initial_pending = response1.data["totals"]["pending_organizers"]
        initial_verified = response1.data["totals"]["verified_organizers"]

        self.pending_org1.is_verified = True
        self.pending_org1.is_active = True
        self.pending_org1.save()

        response2 = self.client.get(url)
        new_pending = response2.data["totals"]["pending_organizers"]
        new_verified = response2.data["totals"]["verified_organizers"]

        self.assertEqual(new_pending, initial_pending - 1)
        self.assertEqual(new_verified, initial_verified + 1)

    def test_dashboard_api_endpoint_works(self):
        """API-specific dashboard endpoint works."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats_api")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("totals", response.data)
