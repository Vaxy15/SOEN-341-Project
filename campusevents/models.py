"""Django models for organizations and events."""

import io
import json
import uuid

import qrcode
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.files.base import ContentFile
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        # Ensure username exists to satisfy AbstractUser unique constraint
        extra_fields.setdefault("username", email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    ROLE_STUDENT = "student"
    ROLE_ORGANIZER = "organizer"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = [
        (ROLE_STUDENT, "Student"),
        (ROLE_ORGANIZER, "Organizer"),
        (ROLE_ADMIN, "Administrator"),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    student_id = models.CharField(max_length=20, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to="profiles/", null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    def __str__(self) -> str:
        full = f"{self.first_name} {self.last_name}".strip()
        return f"{full} ({self.email})" if full else self.email

    # Helpers
    def is_student(self) -> bool:
        return self.role == self.ROLE_STUDENT

    def is_organizer(self) -> bool:
        return self.role == self.ROLE_ORGANIZER

    def is_admin(self) -> bool:
        return self.role == self.ROLE_ADMIN


class Organization(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    approved = models.BooleanField(default=False)

    def __str__(self) -> str:
        return str(self.name)


class Event(models.Model):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    STATUS_CHOICES = [
        (DRAFT, "Draft"),
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    title = models.CharField(max_length=160)
    description = models.TextField()
    category = models.CharField(max_length=80, blank=True)
    location = models.CharField(max_length=160)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(default=0)
    ticket_type = models.CharField(
        max_length=10,
        choices=[("free", "Free"), ("paid", "Paid")],
        default="free",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING,
    )
    admin_comment = models.TextField(blank=True, null=True, help_text="Admin comment when rejecting or modifying event")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return str(self.title)

    @property
    def remaining_capacity(self) -> int:
        """Return remaining ticket capacity, never below zero."""
        issued = 0
        # If a reverse relation named "tickets" exists, count issued tickets.
        # (If not, this safely stays at 0.)
        if hasattr(self, "tickets"):
            issued = self.tickets.filter(status="issued").count()
        return max(0, self.capacity - issued)


class Ticket(models.Model):
    """Ticket model for event attendance with QR code generation."""

    ISSUED = "issued"
    USED = "used"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

    STATUS_CHOICES = [
        (ISSUED, "Issued"),
        (USED, "Used"),
        (CANCELLED, "Cancelled"),
        (EXPIRED, "Expired"),
    ]

    # Relationships
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="tickets")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tickets")

    # Ticket details
    ticket_id = models.CharField(max_length=50, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ISSUED)

    # QR Code
    qr_code = models.ImageField(upload_to="qr_codes/", blank=True, null=True)
    qr_code_data = models.TextField(blank=True)  # Store QR code data for validation

    # Timestamps
    issued_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    # Additional fields
    seat_number = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-issued_at"]
        unique_together = ["event", "user"]  # One ticket per user per event

    def __str__(self) -> str:
        return f"Ticket {self.ticket_id} for {self.event.title}"

    def save(self, *args, **kwargs):
        """Generate ticket ID and QR code on save."""
        if not self.ticket_id:
            # Generate unique ticket ID
            self.ticket_id = f"TKT-{uuid.uuid4().hex[:12].upper()}"

        # Generate QR code data
        if not self.qr_code_data:
            self.qr_code_data = self.generate_qr_data()

        # Generate QR code image
        if not self.qr_code:
            self.generate_qr_code()

        super().save(*args, **kwargs)

    def generate_qr_data(self) -> str:
        """Generate QR code data string."""
        data = {
            "ticket_id": self.ticket_id,
            "event_id": self.event.id,
            "user_id": self.user.id,
            "event_title": self.event.title,
            "user_name": f"{self.user.first_name} {self.user.last_name}",
            "issued_at": self.issued_at.isoformat(),
        }
        return json.dumps(data)

    def generate_qr_code(self):
        """Generate QR code image and save to qr_code field."""
        if not self.qr_code_data:
            return

        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.qr_code_data)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        # Save to model
        filename = f"ticket_{self.ticket_id}.png"
        self.qr_code.save(
            filename,
            ContentFile(buffer.getvalue()),
            save=False
        )

    def is_valid(self) -> bool:
        """Check if ticket is valid for use."""
        return (
            self.status == self.ISSUED and
            (not self.expires_at or self.expires_at > timezone.now()) and
            self.event.status == Event.APPROVED
        )

    def use_ticket(self):
        """Mark ticket as used."""
        if self.is_valid():
            self.status = self.USED
            self.used_at = timezone.now()
            self.save()
            return True
        return False

    def cancel_ticket(self):
        """Cancel the ticket."""
        self.status = self.CANCELLED
        self.save()

    @property
    def qr_code_url(self) -> str:
        """Get QR code URL for API responses."""
        if self.qr_code:
            return self.qr_code.url
        return None
