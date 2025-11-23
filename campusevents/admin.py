# campusevents/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Organization, Event, Ticket, EmailLog

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "is_staff",
        "created_at",
    )
    ordering = ("-created_at",)
    search_fields = ("email", "first_name", "last_name", "student_id")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "student_id",
                    "phone_number",
                    "date_of_birth",
                    "profile_picture",
                )
            },
        ),
        (
            "Permissions",
            {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "role", "password1", "password2"),
            },
        ),
    )

    readonly_fields = ("created_at", "updated_at", "date_joined", "last_login")


@admin.register(Organization)
class OrgAdmin(admin.ModelAdmin):
    list_display = ("name", "approved")
    list_filter = ("approved",)
    search_fields = ("name",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "org", "start_at", "capacity", "status")
    list_filter = ("status", "org", "category")
    search_fields = ("title", "description")
    readonly_fields = ("stats",)

    def stats(self, obj):
        return f"Remaining capacity: {obj.remaining_capacity}"


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_id", "event", "user", "status", "issued_at")
    list_filter = ("status", "event", "issued_at")
    search_fields = ("ticket_id", "user__email", "event__title")
    readonly_fields = ("ticket_id", "qr_code_data", "issued_at", "used_at")

    fieldsets = (
        (None, {"fields": ("ticket_id", "event", "user", "status")}),
        ("QR Code", {"fields": ("qr_code", "qr_code_data")}),
        ("Timestamps", {"fields": ("issued_at", "used_at", "expires_at")}),
        ("Additional", {"fields": ("seat_number", "notes")}),
    )


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("to", "subject", "status", "created_at", "sent_at", "user", "event_id", "ticket_id")
    list_filter = ("status",)
    search_fields = ("to", "subject", "last_error", "message_id", "send_key")
    readonly_fields = ("created_at", "sent_at")
