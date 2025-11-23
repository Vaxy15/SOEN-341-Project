from django.apps import AppConfig
import os
import sys

class CampuseventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "campusevents"

    def ready(self):
        # DO NOT import .signals in tests (prevents double emails & Celery usage)

        if os.environ.get("RUN_TICKET_SIGNAL") == "1" and "pytest" not in sys.modules:
            pass  # pragma: no cover
