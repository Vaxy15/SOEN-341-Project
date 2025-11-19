from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required

from campusevents.models import Ticket, EmailLog
from campusevents.tasks import send_confirmation_task  # or your task name
from campusevents.emails import build_confirmation_message, make_send_key
from campusevents.email_tokens import read_email_token

@login_required
@require_POST
@login_required
@require_POST
def resend_confirmation(request, pk: int):
    ticket = get_object_or_404(Ticket, pk=pk)
    if ticket.user_id != request.user.id:
        return HttpResponseForbidden("Not your ticket")

    since = timezone.now() - timezone.timedelta(days=1)
    recent = EmailLog.objects.filter(
        ticket_id=str(ticket.id),
        to=request.user.email,
        created_at__gte=since
    ).count()
    if recent >= 3:
        return JsonResponse({"ok": False, "error": "Rate limit: 3 per 24h"}, status=429)

    event = ticket.event
    ctx = {
        "user_name": request.user.get_full_name() or request.user.email,
        "event_title": event.title,
        "event_dt": event.start_at,
        "location": event.location,
        "ticket_id": ticket.ticket_id,
        "seat": ticket.seat_number or None,
        "organizer": getattr(event, "org", None).name if hasattr(event, "org") else "",
        "support_email": getattr(settings, "DEFAULT_FROM_EMAIL", "support@example.com"),
    }
    template_path = "campusevents/email/claim_confirmation.html"
    send_key = make_send_key(request.user.email, ticket.ticket_id, template_path)

    log = EmailLog.objects.create(
        to=request.user.email,
        subject=f"Your ticket for {event.title}",
        template=template_path,
        context_json=ctx,
        status="queued",
        user=request.user,
        event_id=str(event.id),
        ticket_id=str(ticket.id),
        send_key=send_key,
    )

    # 👇 key change is here
    transaction.on_commit(lambda: send_confirmation_task.delay(ticket.id))

    return JsonResponse({"ok": True})

def view_ticket_signed(request):
    token = request.GET.get("token")
    try:
        payload = read_email_token(token, max_age_seconds=3600)
    except Exception:
        return HttpResponse("Link expired or invalid.", status=400)
    ticket_code, _, to_email = payload.partition(":")
    ticket = get_object_or_404(Ticket, ticket_id=ticket_code)
    if to_email and to_email.lower() != ticket.user.email.lower():
        return HttpResponse("Token/email mismatch.", status=403)
    return render(request, "campusevents/ticket_view.html", {"ticket": ticket, "event": ticket.event})

@staff_member_required
def preview_claim_email(request, pk: int):
    ticket = get_object_or_404(Ticket, pk=pk)
    msg = build_confirmation_message(
        to_email="dev@example.com",
        user_name="Dev User",
        event_title=ticket.event.title,
        event_dt=ticket.event.start_at,
        location=ticket.event.location,
        ticket_id=ticket.ticket_id,
        seat=ticket.seat_number or None,
        organizer=getattr(ticket.event, "org", None).name if hasattr(ticket.event, "org") else "",
        support_email=getattr(settings, "DEFAULT_FROM_EMAIL", "support@example.com"),
    )
    for alt_body, mime in msg.alternatives:
        if mime == "text/html":
            return HttpResponse(alt_body)
    return HttpResponse(msg.body, content_type="text/plain")
