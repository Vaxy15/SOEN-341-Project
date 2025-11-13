# campusevents/models.py
import io
import json
import uuid
import qrcode
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings



class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
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

    def __str__(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return f"{full} ({self.email})" if full else self.email

    def is_student(self):
        return self.role == self.ROLE_STUDENT

    def is_organizer(self):
        return self.role == self.ROLE_ORGANIZER

    def is_admin(self):
        return self.role == self.ROLE_ADMIN


class Organization(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return self.name


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
    admin_comment = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    # timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def remaining_capacity(self):
        issued = 0
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

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="tickets")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tickets")

    ticket_id = models.CharField(max_length=50, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ISSUED)
    qr_code = models.ImageField(upload_to="qr_codes/", blank=True, null=True)
    qr_code_data = models.TextField(blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    seat_number = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-issued_at"]
        unique_together = ["event", "user"]

    def __str__(self):
        return f"Ticket {self.ticket_id} for {self.event.title}"

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            self.ticket_id = f"TKT-{uuid.uuid4().hex[:12].upper()}"
        if not self.qr_code_data:
            self.qr_code_data = self.generate_qr_data()
        if not self.qr_code:
            self.generate_qr_code()
        super().save(*args, **kwargs)

    def generate_qr_data(self):
        data = {
            "ticket_id": self.ticket_id,
            "event_id": self.event.id,
            "user_id": self.user.id,
            "event_title": self.event.title,
            "user_name": f"{self.user.first_name} {self.user.last_name}",
            "issued_at": self.issued_at.isoformat() if self.issued_at else timezone.now().isoformat(),
        }
        return json.dumps(data)


    def generate_qr_code(self):
        if not self.qr_code_data:
            return
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(self.qr_code_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        self.qr_code.save(f"ticket_{self.ticket_id}.png", ContentFile(buf.getvalue()), save=False)

    def is_valid(self):
        return (
            self.status == self.ISSUED
            and (not self.expires_at or self.expires_at > timezone.now())
            and self.event.status == Event.APPROVED
        )

    def use_ticket(self):
        if self.is_valid():
            self.status = self.USED
            self.used_at = timezone.now()
            self.save()
            return True
        return False

    def cancel_ticket(self):
        self.status = self.CANCELLED
        self.save()

    @property
    def qr_code_url(self):
        if self.qr_code:
            return self.qr_code.url
        return None
class EmailLog(models.Model):
    STATUS_CHOICES = (
        ("queued", "Queued"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    )

    to = models.EmailField()
    subject = models.CharField(max_length=255)
    template = models.CharField(max_length=255)
    context_json = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="queued")
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    message_id = models.CharField(max_length=255, blank=True, default="")
    send_key = models.CharField(max_length=255, db_index=True, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    # light linkage for admin visibility (no hard FK to Event since it’s simple)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    event_id = models.CharField(max_length=64, blank=True, default="")
    ticket_id = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["send_key"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.subject} → {self.to} [{self.status}]"
