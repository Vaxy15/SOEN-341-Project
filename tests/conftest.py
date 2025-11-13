# tests/conftest.py
# Keep lightweight stubs for libs the runner doesn't have, and make tests safe.
import os
import sys
import types
import pytest

# --- Make sure pytest-django knows our settings BEFORE Django imports happen ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campus.settings")

# ----- Stub numpy (yours, kept) -----
def _np_frombuffer(data, dtype=None):
    return data  # our cv2 stub ignores the content anyway

fake_numpy = types.SimpleNamespace(
    uint8=object,
    frombuffer=_np_frombuffer,
)
sys.modules.setdefault("numpy", fake_numpy)

# ----- Stub cv2 (yours, kept) -----
def _cv2_imdecode(arr, flag):
    return None  # simulate "no image" path; tests can monkeypatch if needed

class _FakeQRCodeDetector:
    def detectAndDecode(self, img):
        return ("", None, None)  # "no QR" by default

fake_cv2 = types.SimpleNamespace(
    IMREAD_COLOR=1,
    imdecode=_cv2_imdecode,
    QRCodeDetector=_FakeQRCodeDetector,
)
sys.modules.setdefault("cv2", fake_cv2)

# ----- Stub python-dotenv so campus.settings can import it in CI -----
if "dotenv" not in sys.modules:
    dotenv = types.ModuleType("dotenv")
    def load_dotenv(*args, **kwargs):
        return False  # no-op in CI
    dotenv.load_dotenv = load_dotenv
    sys.modules["dotenv"] = dotenv

# ----- Stub celery so imports and .delay() calls work in CI -----
if "celery" not in sys.modules:
    celery = types.ModuleType("celery")

    def _attach_delay(func):
        # Make func.delay(...) call func(...) synchronously
        def delay(*a, **kw):
            return func(*a, **kw)
        func.delay = delay
        return func

    def shared_task(*dargs, **dkwargs):
        # Decorator that returns the function and adds a .delay alias
        def deco(func):
            return _attach_delay(func)
        return deco

    class Celery:
        def __init__(self, *a, **k):
            pass
        def task(self, *a, **k):
            def deco(f):
                return _attach_delay(f)
            return deco

    celery.shared_task = shared_task
    celery.Celery = Celery
    sys.modules["celery"] = celery

# ----- Test-wide safe overrides -----
@pytest.fixture(autouse=True)
def _settings_overrides(settings):
    # run celery "tasks" inline, no broker needed
    settings.CELERY_TASK_ALWAYS_EAGER = True
    # capture emails in memory for assertions; do not touch real SMTP
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    # keep cache local
    settings.CACHES["default"]["BACKEND"] = "django.core.cache.backends.locmem.LocMemCache"
    # tests shouldn't rely on DEBUG screens
    settings.DEBUG = False
    # be permissive for host checks inside tests
    settings.ALLOWED_HOSTS = ["*"]
