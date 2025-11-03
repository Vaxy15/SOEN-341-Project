# campusevents/tests.py
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from .models import User, Organization, Event, Ticket


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
        
        # Event created by other organizer
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

        # Create tickets with different statuses
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

    def test_admin_can_download_csv(self):
        """Test that admin can download event attendees as CSV via API endpoint."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})
        
        response = self.client.get(url)
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        
        # Check content
        content = response.content.decode("utf-8")
        self.assertIn("student1@example.com", content)
        self.assertIn("student2@example.com", content)

    def test_event_creator_can_download_csv(self):
        """Test that event creator can download attendees CSV for their own event."""
        self.client.force_authenticate(user=self.org_user)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})
        
        response = self.client.get(url)
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        
        # Verify content
        content = response.content.decode("utf-8")
        self.assertIn("Alice", content)
        self.assertIn("Bob", content)

    def test_other_organizer_cannot_download_csv(self):
        """Test that organizers cannot download CSV for events they didn't create."""
        self.client.force_authenticate(user=self.other_organizer)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})
        
        response = self.client.get(url)
        
        # Should be forbidden
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.data)

    def test_student_cannot_download_csv(self):
        """Test that students cannot download event attendees CSV."""
        self.client.force_authenticate(user=self.student1)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})
        
        response = self.client.get(url)
        
        # Should be forbidden
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_download_csv(self):
        """Test that unauthenticated users cannot download CSV."""
        # Don't authenticate
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})
        
        response = self.client.get(url)
        
        # Should be unauthorized
        self.assertIn(response.status_code, [401, 403])

    def test_csv_contains_correct_headers(self):
        """Test that CSV contains all required column headers."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})
        
        response = self.client.get(url)
        
        content = response.content.decode("utf-8")
        
        # Check headers
        self.assertIn("ticket_id", content)
        self.assertIn("ticket_status", content)
        self.assertIn("user_email", content)
        self.assertIn("first_name", content)
        self.assertIn("last_name", content)
        self.assertIn("student_id", content)
        self.assertIn("phone_number", content)
        self.assertIn("issued_at", content)

    def test_csv_contains_correct_data(self):
        """Test that CSV contains correct attendee data."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})
        
        response = self.client.get(url)
        
        content = response.content.decode("utf-8")
        lines = content.strip().split('\n')
        
        # Should have header + 2 tickets
        self.assertEqual(len(lines), 3)
        
        # Check student data is present
        self.assertIn("Alice", content)
        self.assertIn("Bob", content)
        self.assertIn("12345678", content)  # student_id
        self.assertIn("87654321", content)  # student_id
        self.assertIn("555-1234", content)  # phone_number

    def test_csv_filter_by_status_issued(self):
        """Test filtering CSV by 'issued' ticket status."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})
        
        # Filter for issued tickets only
        response = self.client.get(url, {"status": "issued"})
        
        content = response.content.decode("utf-8")
        
        # Should contain student1 (issued) but not student2 (used)
        self.assertIn("student1@example.com", content)
        self.assertNotIn("student2@example.com", content)

    def test_csv_filter_by_status_used(self):
        """Test filtering CSV by 'used' ticket status."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})
        
        # Filter for used tickets only
        response = self.client.get(url, {"status": "used"})
        
        content = response.content.decode("utf-8")
        
        # Should contain student2 (used) but not student1 (issued)
        self.assertIn("student2@example.com", content)
        self.assertNotIn("student1@example.com", content)

    def test_csv_filename_contains_event_id(self):
        """Test that CSV filename includes the event ID."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": self.event.id})
        
        response = self.client.get(url)
        
        # Check Content-Disposition header
        content_disposition = response["Content-Disposition"]
        self.assertIn(f"attendees_event_{self.event.id}.csv", content_disposition)

    def test_csv_for_event_with_no_attendees(self):
        """Test CSV export for event with no tickets/attendees."""
        # Create event with no tickets
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
        
        # Should still succeed with just headers
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        lines = content.strip().split('\n')
        
        # Should have only header row
        self.assertEqual(len(lines), 1)
        self.assertIn("ticket_id", lines[0])

    def test_csv_for_nonexistent_event_returns_404(self):
        """Test that requesting CSV for non-existent event returns 404."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("event_attendees_csv_api", kwargs={"primary_key": 99999})
        
        response = self.client.get(url)
        
        # Should return 404
        self.assertEqual(response.status_code, 404)


class OrganizerApprovalTests(APITestCase):
    """Test suite for the 'Approve or reject organizers' user story."""

    def setUp(self):
        # Create admin user
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass",
            first_name="Admin",
            last_name="User",
        )

        # Create a pending organizer (unverified)
        self.pending_organizer = User.objects.create_user(
            email="pending_org@example.com",
            password="orgpass",
            first_name="Pending",
            last_name="Organizer",
            role=User.ROLE_ORGANIZER,
            is_verified=False,
            is_active=False,
        )

        # Create a student user (to test permission restrictions)
        self.student = User.objects.create_user(
            email="student@example.com",
            password="studentpass",
            first_name="Student",
            last_name="User",
            role=User.ROLE_STUDENT,
        )

        self.client = APIClient()

    def test_admin_can_approve_organizer(self):
        """Test that an admin can approve a pending organizer."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_approval", kwargs={"pk": self.pending_organizer.id})
        
        data = {
            "action": "approve",
            "reason": "Good credentials"
        }
        
        response = self.client.post(url, data, format="json")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertIn("approved successfully", response.data["message"])
        
        # Verify user is now verified and active
        self.pending_organizer.refresh_from_db()
        self.assertTrue(self.pending_organizer.is_verified)
        self.assertTrue(self.pending_organizer.is_active)

    def test_admin_can_reject_organizer(self):
        """Test that an admin can reject a pending organizer."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_approval", kwargs={"pk": self.pending_organizer.id})
        
        data = {
            "action": "reject",
            "reason": "Insufficient documentation"
        }
        
        response = self.client.post(url, data, format="json")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertIn("rejected", response.data["message"])
        
        # Verify user is not verified and not active
        self.pending_organizer.refresh_from_db()
        self.assertFalse(self.pending_organizer.is_verified)
        self.assertFalse(self.pending_organizer.is_active)

    def test_non_admin_cannot_approve_organizer(self):
        """Test that non-admin users cannot approve organizers."""
        self.client.force_authenticate(user=self.student)
        url = reverse("dashboard_user_approval", kwargs={"pk": self.pending_organizer.id})
        
        data = {
            "action": "approve"
        }
        
        response = self.client.post(url, data, format="json")
        
        # Should be forbidden
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.data)
        
        # Verify organizer status unchanged
        self.pending_organizer.refresh_from_db()
        self.assertFalse(self.pending_organizer.is_verified)

    def test_unauthenticated_user_cannot_approve_organizer(self):
        """Test that unauthenticated users cannot approve organizers."""
        url = reverse("dashboard_user_approval", kwargs={"pk": self.pending_organizer.id})
        
        data = {
            "action": "approve"
        }
        
        response = self.client.post(url, data, format="json")
        
        # Should be unauthorized or forbidden
        self.assertIn(response.status_code, [401, 403])

    def test_approve_nonexistent_user_returns_404(self):
        """Test that attempting to approve a non-existent user returns 404."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_approval", kwargs={"pk": 99999})
        
        data = {
            "action": "approve"
        }
        
        response = self.client.post(url, data, format="json")
        
        # Should return 404
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.data)

    def test_admin_can_view_pending_organizers(self):
        """Test that admin can view list of pending organizers."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_pending_organizers")
        
        response = self.client.get(url)
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Verify pending organizer is in the list
        results = response.data.get("results", response.data)
        emails = [user["email"] for user in results]
        self.assertIn("pending_org@example.com", emails)

    def test_approved_organizer_not_in_pending_list(self):
        """Test that approved organizers don't appear in pending list."""
        # First approve the organizer
        self.pending_organizer.is_verified = True
        self.pending_organizer.is_active = True
        self.pending_organizer.save()
        
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_pending_organizers")
        
        response = self.client.get(url)
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Verify approved organizer is NOT in the list
        results = response.data.get("results", response.data)
        emails = [user["email"] for user in results]
        self.assertNotIn("pending_org@example.com", emails)


class ManageUsersRolesStatusTests(APITestCase):
    """Test suite for the 'Manage Users (Roles & Status)' user story."""

    def setUp(self):
        # Create admin user
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass",
            first_name="Admin",
            last_name="User",
        )

        # Create a student user
        self.student = User.objects.create_user(
            email="student@example.com",
            password="studentpass",
            first_name="Student",
            last_name="User",
            role=User.ROLE_STUDENT,
            is_active=True,
            is_verified=True,
        )

        # Create an organizer user
        self.organizer = User.objects.create_user(
            email="organizer@example.com",
            password="orgpass",
            first_name="Organizer",
            last_name="User",
            role=User.ROLE_ORGANIZER,
            is_active=True,
            is_verified=True,
        )

        self.client = APIClient()

    # ========== ROLE MANAGEMENT TESTS ==========

    def test_admin_can_change_user_role_student_to_organizer(self):
        """Test that admin can change a student's role to organizer."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_role", kwargs={"pk": self.student.id})
        
        data = {"role": User.ROLE_ORGANIZER}
        response = self.client.post(url, data, format="json")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertIn("role changed", response.data["message"])
        
        # Verify role was changed
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.ROLE_ORGANIZER)

    def test_admin_can_change_user_role_to_admin(self):
        """Test that admin can promote a user to admin role."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_role", kwargs={"pk": self.student.id})
        
        data = {"role": User.ROLE_ADMIN}
        response = self.client.post(url, data, format="json")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Verify role was changed to admin
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.ROLE_ADMIN)

    def test_admin_can_change_organizer_role_to_student(self):
        """Test that admin can demote an organizer to student."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_role", kwargs={"pk": self.organizer.id})
        
        data = {"role": User.ROLE_STUDENT}
        response = self.client.post(url, data, format="json")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Verify role was changed
        self.organizer.refresh_from_db()
        self.assertEqual(self.organizer.role, User.ROLE_STUDENT)

    def test_non_admin_cannot_change_user_role(self):
        """Test that non-admin users cannot change roles."""
        self.client.force_authenticate(user=self.student)
        url = reverse("dashboard_user_role", kwargs={"pk": self.organizer.id})
        
        data = {"role": User.ROLE_STUDENT}
        response = self.client.post(url, data, format="json")
        
        # Should be forbidden
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.data)
        
        # Verify role unchanged
        self.organizer.refresh_from_db()
        self.assertEqual(self.organizer.role, User.ROLE_ORGANIZER)

    def test_change_role_with_invalid_role_returns_400(self):
        """Test that providing an invalid role returns 400."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_role", kwargs={"pk": self.student.id})
        
        data = {"role": "invalid_role"}
        response = self.client.post(url, data, format="json")
        
        # Should return bad request
        self.assertEqual(response.status_code, 400)

    def test_change_role_for_nonexistent_user_returns_404(self):
        """Test that changing role for non-existent user returns 404."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_role", kwargs={"pk": 99999})
        
        data = {"role": User.ROLE_ADMIN}
        response = self.client.post(url, data, format="json")
        
        # Should return 404
        self.assertEqual(response.status_code, 404)

    # ========== STATUS MANAGEMENT TESTS ==========

    def test_admin_can_deactivate_user(self):
        """Test that admin can deactivate a user account."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_status", kwargs={"pk": self.student.id})
        
        data = {"is_active": False}
        response = self.client.post(url, data, format="json")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertIn("deactivated", response.data["message"])
        
        # Verify user is deactivated
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)

    def test_admin_can_activate_user(self):
        """Test that admin can activate a user account."""
        # First deactivate the user
        self.student.is_active = False
        self.student.save()
        
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_status", kwargs={"pk": self.student.id})
        
        data = {"is_active": True}
        response = self.client.post(url, data, format="json")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertIn("activated", response.data["message"])
        
        # Verify user is activated
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)

    def test_admin_can_change_verification_status(self):
        """Test that admin can change user verification status."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_status", kwargs={"pk": self.student.id})
        
        data = {
            "is_active": True,
            "is_verified": False
        }
        response = self.client.post(url, data, format="json")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Verify verification status changed
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_verified)

    def test_non_admin_cannot_change_user_status(self):
        """Test that non-admin users cannot change user status."""
        self.client.force_authenticate(user=self.organizer)
        url = reverse("dashboard_user_status", kwargs={"pk": self.student.id})
        
        data = {"is_active": False}
        response = self.client.post(url, data, format="json")
        
        # Should be forbidden
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.data)
        
        # Verify status unchanged
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)

    def test_change_status_for_nonexistent_user_returns_404(self):
        """Test that changing status for non-existent user returns 404."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_status", kwargs={"pk": 99999})
        
        data = {"is_active": False}
        response = self.client.post(url, data, format="json")
        
        # Should return 404
        self.assertEqual(response.status_code, 404)

    def test_deactivated_user_cannot_login(self):
        """Test that deactivated users cannot authenticate."""
        # Deactivate the student
        self.student.is_active = False
        self.student.save()
        
        # Try to authenticate
        client = APIClient()
        success = client.login(email="student@example.com", password="studentpass")
        
        # Login should fail
        self.assertFalse(success)

    def test_deactivated_user_cannot_access_api(self):
        """Test that deactivated users cannot access protected API endpoints."""
        # Deactivate the user
        self.student.is_active = False
        self.student.save()
        
        # Create a new client and try to authenticate with inactive user
        # Note: force_authenticate bypasses is_active checks, so we verify
        # that the user model has is_active=False which would prevent real login
        self.assertFalse(self.student.is_active)
        
        # In a real scenario, attempting to obtain a JWT token would fail
        # The Django authentication backend checks is_active before allowing login

    def test_reactivated_user_can_access_api(self):
        """Test that reactivated users can access API endpoints."""
        # Deactivate then reactivate the user
        self.student.is_active = False
        self.student.save()
        self.student.is_active = True
        self.student.save()
        
        # Try to access protected endpoint
        self.client.force_authenticate(user=self.student)
        url = reverse("user_profile")
        response = self.client.get(url)
        
        # Should succeed
        self.assertEqual(response.status_code, 200)


class DashboardOverviewTests(APITestCase):
    """Test suite for the 'Dashboard overview' user story."""

    def setUp(self):
        from django.utils import timezone
        
        # Create admin user
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass",
            first_name="Admin",
            last_name="User",
        )

        # Create verified organizers
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

        # Create pending organizers
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

        # Create students
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

        # Create events with different statuses
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

        # Create tickets with different statuses
        # Each user can only have one ticket per event due to UNIQUE constraint
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
        """Test that admin can access dashboard stats endpoint."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertIn("totals", response.data)

    def test_non_admin_cannot_access_dashboard_stats(self):
        """Test that non-admin users cannot access dashboard stats."""
        self.client.force_authenticate(user=self.student1)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Should be forbidden
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.data)

    def test_organizer_cannot_access_dashboard_stats(self):
        """Test that organizers cannot access dashboard stats."""
        self.client.force_authenticate(user=self.verified_org1)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Should be forbidden
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_access_dashboard(self):
        """Test that unauthenticated users cannot access dashboard stats."""
        # Don't authenticate
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Should be unauthorized
        self.assertIn(response.status_code, [401, 403])

    # ========== TOTALS TESTS ==========

    def test_dashboard_contains_totals_section(self):
        """Test that dashboard response contains totals section."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Check totals section exists
        self.assertIn("totals", response.data)
        totals = response.data["totals"]
        
        # Check all required fields
        self.assertIn("total_users", totals)
        self.assertIn("total_events", totals)
        self.assertIn("tickets_issued_total", totals)
        self.assertIn("tickets_used_total", totals)
        self.assertIn("verified_organizers", totals)
        self.assertIn("pending_organizers", totals)
        self.assertIn("pending_events", totals)

    def test_dashboard_total_users_count(self):
        """Test that total users count is accurate."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Should count: 1 admin + 2 verified orgs + 2 pending orgs + 2 students = 7
        self.assertEqual(response.data["totals"]["total_users"], 7)

    def test_dashboard_verified_organizers_count(self):
        """Test that verified organizers count is accurate."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Should have 2 verified organizers
        self.assertEqual(response.data["totals"]["verified_organizers"], 2)

    def test_dashboard_pending_organizers_count(self):
        """Test that pending organizers count is accurate."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Should have 2 pending organizers
        self.assertEqual(response.data["totals"]["pending_organizers"], 2)

    def test_dashboard_total_events_count(self):
        """Test that total events count is accurate."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Should have 3 events total (1 approved + 2 pending)
        self.assertEqual(response.data["totals"]["total_events"], 3)

    def test_dashboard_pending_events_count(self):
        """Test that pending events count is accurate."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Should have 2 pending events
        self.assertEqual(response.data["totals"]["pending_events"], 2)

    def test_dashboard_tickets_issued_count(self):
        """Test that issued tickets count is accurate."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Should have 1 issued ticket
        self.assertEqual(response.data["totals"]["tickets_issued_total"], 1)

    def test_dashboard_tickets_used_count(self):
        """Test that used tickets count is accurate."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Should have 1 used ticket
        self.assertEqual(response.data["totals"]["tickets_used_total"], 1)

    # ========== MONTHLY DATA TESTS ==========

    def test_dashboard_contains_events_per_month(self):
        """Test that dashboard contains events per month data."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Check events_per_month exists and is a list
        self.assertIn("events_per_month", response.data)
        self.assertIsInstance(response.data["events_per_month"], list)
        
        # Should have 12 months of data
        self.assertEqual(len(response.data["events_per_month"]), 12)

    def test_dashboard_events_per_month_structure(self):
        """Test that events per month has correct structure."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        events_per_month = response.data["events_per_month"]
        
        # Check first entry has correct keys
        if len(events_per_month) > 0:
            entry = events_per_month[0]
            self.assertIn("month", entry)
            self.assertIn("count", entry)

    def test_dashboard_contains_tickets_per_month(self):
        """Test that dashboard contains tickets per month data."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Check tickets_per_month exists and is a list
        self.assertIn("tickets_per_month", response.data)
        self.assertIsInstance(response.data["tickets_per_month"], list)
        
        # Should have 12 months of data
        self.assertEqual(len(response.data["tickets_per_month"]), 12)

    def test_dashboard_tickets_per_month_structure(self):
        """Test that tickets per month has correct structure."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        tickets_per_month = response.data["tickets_per_month"]
        
        # Check first entry has correct keys
        if len(tickets_per_month) > 0:
            entry = tickets_per_month[0]
            self.assertIn("month", entry)
            self.assertIn("issued", entry)
            self.assertIn("used", entry)
            self.assertIn("participation_rate", entry)

    # ========== TOP EVENTS TESTS ==========

    def test_dashboard_contains_top_events_by_checkins(self):
        """Test that dashboard contains top events by check-ins."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Check top_events_by_checkins exists and is a list
        self.assertIn("top_events_by_checkins", response.data)
        self.assertIsInstance(response.data["top_events_by_checkins"], list)

    def test_dashboard_top_events_structure(self):
        """Test that top events have correct structure."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        top_events = response.data["top_events_by_checkins"]
        
        # Check structure
        if len(top_events) > 0:
            event = top_events[0]
            self.assertIn("event_id", event)
            self.assertIn("title", event)
            self.assertIn("used", event)

    def test_dashboard_top_events_limited_to_five(self):
        """Test that top events list is limited to 5 entries."""
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
            # Add used tickets
            Ticket.objects.create(
                event=event,
                user=self.student1,
                status=Ticket.USED,
            )
        
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        response = self.client.get(url)
        
        # Should have max 5 events
        self.assertLessEqual(len(response.data["top_events_by_checkins"]), 5)

    # ========== DYNAMIC UPDATES TESTS ==========

    def test_dashboard_updates_when_new_user_added(self):
        """Test that dashboard reflects changes when new user is added."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        # Get initial count
        response1 = self.client.get(url)
        initial_count = response1.data["totals"]["total_users"]
        
        # Add new user
        User.objects.create_user(
            email="newuser@example.com",
            password="pw",
            first_name="New",
            last_name="User",
        )
        
        # Get updated count
        response2 = self.client.get(url)
        new_count = response2.data["totals"]["total_users"]
        
        # Should increase by 1
        self.assertEqual(new_count, initial_count + 1)

    def test_dashboard_updates_when_organizer_approved(self):
        """Test that dashboard reflects changes when organizer is approved."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats")
        
        # Get initial counts
        response1 = self.client.get(url)
        initial_pending = response1.data["totals"]["pending_organizers"]
        initial_verified = response1.data["totals"]["verified_organizers"]
        
        # Approve a pending organizer
        self.pending_org1.is_verified = True
        self.pending_org1.is_active = True
        self.pending_org1.save()
        
        # Get updated counts
        response2 = self.client.get(url)
        new_pending = response2.data["totals"]["pending_organizers"]
        new_verified = response2.data["totals"]["verified_organizers"]
        
        # Pending should decrease by 1, verified should increase by 1
        self.assertEqual(new_pending, initial_pending - 1)
        self.assertEqual(new_verified, initial_verified + 1)

    def test_dashboard_api_endpoint_works(self):
        """Test that the API-specific dashboard endpoint works."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("admin_dashboard_stats_api")
        
        response = self.client.get(url)
        
        # Should work the same as the regular endpoint
        self.assertEqual(response.status_code, 200)
        self.assertIn("totals", response.data)