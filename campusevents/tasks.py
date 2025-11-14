from __future__ import annotations
# --- Celery shim for CI (lets .delay() work even if celery isn't installed) ---
try:
    from celery import shared_task  # real celery when available
except Exception:
    class _EagerTaskWrapper:
        def __init__(self, f):
            self._f = f
        def __call__(self, *a, **k):
            return self._f(*a, **k)
        def delay(self, *a, **k):
            return self._f(*a, **k)
        apply_async = delay
    def shared_task(func=None, **kwargs):
        if func is None:
            def deco(f): return _EagerTaskWrapper(f)
            return deco
        return _EagerTaskWrapper(func)
# -------------------------------------------------------------------------------


# ---- Optional Celery shim (so .delay works in CI without celery) ----
try:
    from celery import shared_task  # real decorator if celery installed
except Exception:
    def shared_task(func=None, **_kwargs):
        def decorator(f):
            # mimic Celery's .delay by calling inline
            f.delay = lambda *a, **k: f(*a, **k)
            return f
        return decorator(func) if func else decorator
# --------------------------------------------------------------------

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from .models import Ticket


@shared_task
def send_ticket_confirmation_email(ticket_id: int) -> None:
    """Send a simple ticket confirmation email. Safe in CI and dev."""
    try:
        ticket = Ticket.objects.select_related("event", "user").get(id=ticket_id)
    except Ticket.DoesNotExist:
        return

    base = getattr(settings, "APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

    # Try to build a link to the ticket page; fall back to base site.
    try:
        detail_path = reverse("ticket_detail_page", args=[ticket.id])
    except Exception:
        detail_path = "/"

    subject = f"Your ticket for {ticket.event.title}"
    greeting_name = ticket.user.get_full_name() or ticket.user.username or "there"
    body = (
        f"Hi {greeting_name},\n\n"
        f"Your ticket has been issued for:\n"
        f"  • Event: {ticket.event.title}\n"
        f"  • Ticket ID: {ticket.ticket_id}\n\n"
        f"View your ticket: {base}{detail_path}\n\n"
        f"-- Campus Events"
    )

    to_list = [ticket.user.email] if ticket.user.email else []
    if not to_list:
        return  # nothing to send to

    send_mail(
        subject,
        body,
        getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
        to_list,
        fail_silently=True,  # never crash tests/CI on email errors
    )
