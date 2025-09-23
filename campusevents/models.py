from django.db import models
from django.contrib.auth.models import User

class Organization(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    approved = models.BooleanField(default=False)
    def __str__(self): return self.name

class Event(models.Model):
    DRAFT,PENDING,APPROVED,REJECTED = "draft","pending","approved","rejected"
    STATUS_CHOICES = [(DRAFT,"Draft"),(PENDING,"Pending"),(APPROVED,"Approved"),(REJECTED,"Rejected")]

    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    title = models.CharField(max_length=160)
    description = models.TextField()
    category = models.CharField(max_length=80, blank=True)
    location = models.CharField(max_length=160)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(default=0)
    ticket_type = models.CharField(max_length=10, choices=[("free","Free"),("paid","Paid")], default="free")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self): return self.title

    @property
    def remaining_capacity(self):
        issued = self.tickets.filter(status="issued").count() if hasattr(self, "tickets") else 0
        return max(0, self.capacity - issued)
