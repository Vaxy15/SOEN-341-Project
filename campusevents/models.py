"""Django models for organizations and events."""

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


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
