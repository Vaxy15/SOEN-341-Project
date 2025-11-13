from django.apps import AppConfig

class CampuseventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "campusevents"

    # Keep ready() but do nothing (signals disabled to avoid double emails)
    def ready(self):
        # from . import signals
        pass
