# campusevents/tasks.py

from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.mail import get_connection
from django.utils import timezone

from .models import EmailLog, Ticket
from .emails import build_confirmation_message, make_send_key


# ---------- helpers ----------

def _iso(dt):
    if not dt:
        return None
    return timezone.localtime(dt).isoformat()

def _human(dt):
    if not dt:
        return ""
    dt = timezone.localtime(dt)
    return dt.strftime("%a, %b %d %Y, %I:%M %p %Z")

def _range_human(start, end):
    s = _human(start)
    e = _human(end) if end else ""
    return f"{s} → {e}" if e else s


def _send_from_log(log: EmailLog):
    # Prevent re-sends if a retry lands after success
    if log.status == "sent":
        return
    ctx = log.context_json 

    # one display field only; builder expects "event_dt"
    event_dt_display = ctx.get("event_dt", "")

    msg = build_confirmation_message(
        to_email=log.to,
        user_name=ctx.get("user_name", ""),
        event_title=ctx.get("event_title", ""),
        event_dt=event_dt_display,
        location=ctx.get("location", ""),
        ticket_id=ctx.get("ticket_id", ""),
        seat=ctx.get("seat"),
        organizer=ctx.get("organizer", ""),
        support_email=ctx.get("support_email", settings.DEFAULT_FROM_EMAIL),
    )

    sent_count = 0
    last_error = ""
    try:
        with get_connection() as conn:
            sent_count = conn.send_messages([msg]) or 0
    except Exception as exc:
        last_error = str(exc)

    log.status = "sent" if sent_count > 0 else "failed"
    log.sent_at = timezone.now()
    log.message_id = getattr(msg, "extra_headers", {}).get("Message-ID", "")
    log.last_error = last_error
    log.save(update_fields=["status", "sent_at", "message_id", "last_error"])


# ---------- tasks ----------

@shared_task(bind=True, max_retries=5, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True)
def send_confirmation_task(self, log_id: int):
    log = EmailLog.objects.get(id=log_id)
    if log.status == "sent":
        return {"log_id": log.id, "status": "already_sent"}
    _send_from_log(log)
    return {"log_id": log.id, "status": log.status}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={"max_retries": 5})
def send_ticket_confirmation_email(self, ticket_id: int):
    t = Ticket.objects.select_related("event", "user").get(id=ticket_id)

    # preformat a single, JSON-safe string for the range
    event_dt_display = _range_human(t.event.start_at, t.event.end_at)

    ctx = {
        "user_name": (f"{t.user.first_name} {t.user.last_name}".strip() or t.user.email),
        "event_title": t.event.title,
        "event_dt": event_dt_display,     # single field (what the builder expects)
        "location": t.event.location,
        "ticket_id": t.ticket_id,
        "seat": t.seat_number or None,
        "organizer": getattr(t.event, "org", None).name if hasattr(t.event, "org") and t.event.org else "",
        "support_email": getattr(settings, "DEFAULT_FROM_EMAIL", "support@example.com"),
    }

    template_path = "campusevents/email/claim_confirmation.html"
    send_key = make_send_key(t.user.email, t.ticket_id, template_path)

    already = EmailLog.objects.filter(send_key=send_key, status="sent").first()
    if already:
        return {"log_id": already.id, "status": "already_sent"}

    log = EmailLog.objects.create(
        to=t.user.email,
        subject=f"Your ticket for {t.event.title}",
        template=template_path,
        context_json=ctx,
        status="queued",
        user=t.user,
        event_id=str(t.event.id),
        ticket_id=str(t.id),
        send_key=send_key,
    )

    result = send_confirmation_task.delay(log.id)
    return {"queued_log_id": log.id, "send_task_id": str(result.id)}
