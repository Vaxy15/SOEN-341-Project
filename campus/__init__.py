# campus/__init__.py
try:
    from .celery import app as celery_app  # noqa: F401
except Exception:
    celery_app = None  # Celery is optional in test/CI
