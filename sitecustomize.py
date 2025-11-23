import os
import sys

# Ensure Django settings are available before pytest-django scans.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campus.settings")

# In CI / pytest, run Celery tasks inline and avoid real SMTP/brokers.
argv = " ".join(sys.argv).lower()
if "pytest" in argv or os.environ.get("GITHUB_ACTIONS") == "true":
    os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")
    os.environ.setdefault("CELERY_BROKER_URL", "memory://")
    os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")
    os.environ.setdefault("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
