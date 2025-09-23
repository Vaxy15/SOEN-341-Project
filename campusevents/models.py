"""Django models for organizations and events."""

from django.db import models
from django.contrib.auth.models import User


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
