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

    # Lazy import to avoid circular imports
    try:
        from .emails import build_confirmation_message  # type: ignore
    except Exception:
        build_confirmation_message = None  # type: ignore[assignment]

    event = ticket.event
    user = ticket.user

    # Use the SAME context keys your templates & preview use
    ctx = {
        "user_name": user.get_full_name() or user.email,
        "event_title": event.title,
        "event_dt": event.start_at,
        "location": event.location,
        "ticket_id": ticket.ticket_id,
        "seat": ticket.seat_number or None,
        "organizer": getattr(event, "org", None).name if hasattr(event, "org") else "",
        "support_email": getattr(settings, "DEFAULT_FROM_EMAIL", "support@example.com"),
        "site_url": getattr(
            settings, "APP_BASE_URL", getattr(settings, "SITE_URL", "")
        ),
    }

    # 1) Preferred path: use the canonical builder
    if build_confirmation_message:
        try:
            msg = build_confirmation_message(
                to_email=user.email,
                user_name=ctx["user_name"],
                event_title=ctx["event_title"],
                event_dt=ctx["event_dt"],
                location=ctx["location"],
                ticket_id=ctx["ticket_id"],
                seat=ctx["seat"],
                organizer=ctx["organizer"],
                support_email=ctx["support_email"],
            )
            msg.send(fail_silently=not settings.DEBUG)
            return {"ticket_id": ticket.id, "email_to": user.email}
        except Exception:
            # if something unexpected happens, fall back to manual render
            pass

    # 2) Fallback: manual multi-part email using the SAME ctx keys
    subject = f"Your ticket for {ctx['event_title']}"
    text_body = render_to_string("campusevents/email/claim_confirmation.txt", ctx)
    try:
        html_body = render_to_string(
            "campusevents/email/claim_confirmation.html", ctx
        )
    except Exception:
        html_body = None

    connection = get_connection()
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=ctx["support_email"],
        to=[user.email],
        connection=connection,
    )
    if html_body:
        email.attach_alternative(html_body, "text/html")

    email.send(fail_silently=not settings.DEBUG)

    return {"ticket_id": ticket.id, "email_to": user.email}


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
