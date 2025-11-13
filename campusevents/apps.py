from django.apps import AppConfig

class CampuseventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "campusevents"

    def ready(self):
        # DO NOT import .signals in tests (prevents double emails & Celery usage)
        import os, sys
        if os.environ.get("RUN_TICKET_SIGNAL") == "1" and "pytest" not in sys.modules:
            from . import signals  # pragma: no cover
