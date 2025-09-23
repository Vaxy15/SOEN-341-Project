from django.contrib import admin
from .models import Organization, Event

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
