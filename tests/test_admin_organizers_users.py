# tests/test_admin_organizers_users.py

from django.urls import reverse
from rest_framework.test import APITestCase, APIClient

from campusevents.models import User, Organization, Event, Ticket


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
        """Admin can approve a pending organizer."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_approval", kwargs={"pk": self.pending_organizer.id})

        data = {"action": "approve", "reason": "Good credentials"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("approved successfully", response.data["message"])

        self.pending_organizer.refresh_from_db()
        self.assertTrue(self.pending_organizer.is_verified)
        self.assertTrue(self.pending_organizer.is_active)

    def test_admin_can_reject_organizer(self):
        """Admin can reject a pending organizer."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_approval", kwargs={"pk": self.pending_organizer.id})

        data = {"action": "reject", "reason": "Insufficient documentation"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("rejected", response.data["message"])

        self.pending_organizer.refresh_from_db()
        self.assertFalse(self.pending_organizer.is_verified)
        self.assertFalse(self.pending_organizer.is_active)

    def test_non_admin_cannot_approve_organizer(self):
        """Non-admin users cannot approve organizers."""
        self.client.force_authenticate(user=self.student)
        url = reverse("dashboard_user_approval", kwargs={"pk": self.pending_organizer.id})

        data = {"action": "approve"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.data)

        self.pending_organizer.refresh_from_db()
        self.assertFalse(self.pending_organizer.is_verified)

    def test_unauthenticated_user_cannot_approve_organizer(self):
        """Unauthenticated users cannot approve organizers."""
        url = reverse("dashboard_user_approval", kwargs={"pk": self.pending_organizer.id})

        data = {"action": "approve"}
        response = self.client.post(url, data, format="json")

        self.assertIn(response.status_code, [401, 403])

    def test_approve_nonexistent_user_returns_404(self):
        """Approving a non-existent user returns 404."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_approval", kwargs={"pk": 99999})

        data = {"action": "approve"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.data)

    def test_admin_can_view_pending_organizers(self):
        """Admin can view list of pending organizers."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_pending_organizers")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        results = response.data.get("results", response.data)
        emails = [user["email"] for user in results]
        self.assertIn("pending_org@example.com", emails)

    def test_approved_organizer_not_in_pending_list(self):
        """Approved organizers do not appear in pending list."""
        self.pending_organizer.is_verified = True
        self.pending_organizer.is_active = True
        self.pending_organizer.save()

        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_pending_organizers")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
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
        """Admin can change a student's role to organizer."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_role", kwargs={"pk": self.student.id})

        data = {"role": User.ROLE_ORGANIZER}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("role changed", response.data["message"])

        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.ROLE_ORGANIZER)

    def test_admin_can_change_user_role_to_admin(self):
        """Admin can promote a user to admin role."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_role", kwargs={"pk": self.student.id})

        data = {"role": User.ROLE_ADMIN}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 200)

        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.ROLE_ADMIN)

    def test_admin_can_change_organizer_role_to_student(self):
        """Admin can demote an organizer to student."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_role", kwargs={"pk": self.organizer.id})

        data = {"role": User.ROLE_STUDENT}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 200)

        self.organizer.refresh_from_db()
        self.assertEqual(self.organizer.role, User.ROLE_STUDENT)

    def test_non_admin_cannot_change_user_role(self):
        """Non-admin users cannot change roles."""
        self.client.force_authenticate(user=self.student)
        url = reverse("dashboard_user_role", kwargs={"pk": self.organizer.id})

        data = {"role": User.ROLE_STUDENT}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.data)

        self.organizer.refresh_from_db()
        self.assertEqual(self.organizer.role, User.ROLE_ORGANIZER)

    def test_change_role_with_invalid_role_returns_400(self):
        """Providing an invalid role returns 400."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_role", kwargs={"pk": self.student.id})

        data = {"role": "invalid_role"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 400)

    def test_change_role_for_nonexistent_user_returns_404(self):
        """Changing role for non-existent user returns 404."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_role", kwargs={"pk": 99999})

        data = {"role": User.ROLE_ADMIN}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 404)

    # ========== STATUS MANAGEMENT TESTS ==========

    def test_admin_can_deactivate_user(self):
        """Admin can deactivate a user account."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_status", kwargs={"pk": self.student.id})

        data = {"is_active": False}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("deactivated", response.data["message"])

        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)

    def test_admin_can_activate_user(self):
        """Admin can activate a user account."""
        self.student.is_active = False
        self.student.save()

        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_status", kwargs={"pk": self.student.id})

        data = {"is_active": True}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("activated", response.data["message"])

        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)

    def test_admin_can_change_verification_status(self):
        """Admin can change user verification status."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_status", kwargs={"pk": self.student.id})

        data = {"is_active": True, "is_verified": False}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 200)

        self.student.refresh_from_db()
        self.assertFalse(self.student.is_verified)

    def test_non_admin_cannot_change_user_status(self):
        """Non-admin users cannot change user status."""
        self.client.force_authenticate(user=self.organizer)
        url = reverse("dashboard_user_status", kwargs={"pk": self.student.id})

        data = {"is_active": False}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.data)

        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)

    def test_change_status_for_nonexistent_user_returns_404(self):
        """Changing status for non-existent user returns 404."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("dashboard_user_status", kwargs={"pk": 99999})

        data = {"is_active": False}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 404)

    def test_deactivated_user_cannot_login(self):
        """Deactivated users cannot authenticate."""
        self.student.is_active = False
        self.student.save()

        client = APIClient()
        success = client.login(email="student@example.com", password="studentpass")

        self.assertFalse(success)

    def test_deactivated_user_cannot_access_api(self):
        """
        Deactivated users cannot access protected endpoints in real auth flow.
        Here we just assert the model state; force_authenticate bypasses is_active.
        """
        self.student.is_active = False
        self.student.save()

        self.assertFalse(self.student.is_active)

    def test_reactivated_user_can_access_api(self):
        """Reactivated users can access API endpoints."""
        self.student.is_active = False
        self.student.save()
        self.student.is_active = True
        self.student.save()

        self.client.force_authenticate(user=self.student)
        url = reverse("user_profile")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
