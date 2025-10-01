from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Organization, Event


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
        # placeholder until tickets exist
        return f"Remaining capacity: {obj.remaining_capacity}"
