# campusevents/tasks.py
from __future__ import annotations

# --- Celery (safe shim if Celery isn't installed, e.g., in CI) --------------
try:
    from celery import shared_task  # type: ignore
except Exception:
    def shared_task(*dargs, **dkwargs):
        """Fallback decorator that gives the function a .delay/.apply_async which call it inline."""
        def _decorate(fn):
            def _delay(*args, **kwargs):
                return fn(*args, **kwargs)
            fn.delay = _delay
            fn.apply_async = _delay
            return fn
        if dargs and callable(dargs[0]) and not dkwargs:
            return _decorate(dargs[0])
        return _decorate

# --- Django / app imports -----------------------------------------------------
from django.conf import settings
from django.core.mail import get_connection
from django.core.mail.message import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Ticket


# --- Helpers ------------------------------------------------------------------
def _build_and_send(ticket: Ticket) -> dict:
    """Build and send the ticket confirmation email (text + optional HTML)."""

    # Lazy import here to avoid circular: emails.py might import from tasks.py.
    try:
        from .emails import build_confirmation_message  # type: ignore
    except Exception:
        build_confirmation_message = None  # type: ignore[assignment]

    ctx = {
        "ticket": ticket,
        "event": ticket.event,
        "user": ticket.user,
        "site_url": getattr(settings, "APP_BASE_URL", getattr(settings, "SITE_URL", "")),
        "support_email": getattr(settings, "DEFAULT_FROM_EMAIL", ""),
        "now": timezone.now(),
    }

    if build_confirmation_message:
        try:
            msg = build_confirmation_message(
                to_email=ticket.user.email,
                ticket=ticket,
                event=ticket.event,
                user=ticket.user,
                site_url=ctx["site_url"],
                support_email=ctx["support_email"],
            )
            msg.send(fail_silently=True)
            return {"ticket_id": ticket.id, "email_to": ticket.user.email}
        except Exception:
            pass  # fall through to manual build

    # Fallback: manual multi-part email using templates (HTML optional)
    subject = f"Your ticket for {ticket.event.title}"
    text_body = render_to_string("campusevents/email/claim_confirmation.txt", ctx)
    html_body = None
    try:
        html_body = render_to_string("campusevents/email/claim_confirmation.html", ctx)
    except Exception:
        pass

    connection = get_connection()
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[ticket.user.email],
        connection=connection,
    )
    if html_body:
        email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=True)

    return {"ticket_id": ticket.id, "email_to": ticket.user.email}


# --- Tasks --------------------------------------------------------------------
@shared_task
def send_ticket_confirmation_email(ticket_id: int) -> dict:
    """Primary task your code calls: send confirmation for a Ticket by id."""
    ticket = Ticket.objects.select_related("event", "user").get(id=ticket_id)
    return _build_and_send(ticket)


# Back-compat for CI tests that import `send_confirmation_task`
@shared_task
def send_confirmation_task(ticket_id: int) -> dict:
    return send_ticket_confirmation_email(ticket_id)
