# campusevents/views/organizer_views.py
"""
Organizer-specific views for event management and ticket scanning.
"""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import Event, Ticket
from .utils import decode_qr_from_uploaded


@login_required(login_url='login')
def organizer_my_events(request):
    """
    Page for organizers/admins: list their events and provide a QR image upload
    per event to mark attendance (ticket 'USED') if valid.
    """
    if request.user.role not in ['organizer', 'admin']:
        return redirect('event_list_page')

    events = (
        Event.objects
        .filter(created_by=request.user)
        .order_by('-start_at')
        .prefetch_related('tickets')
    )

    event_cards = []
    for e in events:
        issued = e.tickets.filter(status=Ticket.ISSUED).count()
        used = e.tickets.filter(status=Ticket.USED).count()
        event_cards.append({
            "obj": e,
            "issued": issued,
            "used": used,
            "remaining": e.remaining_capacity,
        })

    return render(request, "organizer_my_events.html", {
        "event_cards": event_cards,
    })


@login_required(login_url='login')
@require_POST
def scan_ticket_image(request, pk):
    event = get_object_or_404(Event, pk=pk)

    # Permissions: organizer/admin OR event owner
    if not (request.user.role in ['organizer', 'admin'] or event.created_by == request.user):
        messages.error(request, "You do not have permission to validate tickets for this event.")
        return redirect('organizer_my_events')

    uploaded = request.FILES.get("qr_image")
    if not uploaded:
        messages.error(request, "Please choose an image file with a QR code.")
        return redirect('organizer_my_events')

    try:
        payload = decode_qr_from_uploaded(uploaded)
    except Exception as ex:
        messages.error(request, f"Could not read the image: {ex}")
        return redirect('organizer_my_events')

    if not payload:
        messages.error(request, "No QR code detected in the image.")
        return redirect('organizer_my_events')

    # The QR we generate is JSON with ticket_id, event_id, etc.
    try:
        data = json.loads(payload)
    except Exception:
        # Some phones might encode the plain ticket_id; try that too
        data = {"ticket_id": payload}

    ticket_id = data.get("ticket_id")
    if not ticket_id:
        messages.error(request, "QR code doesn't include a ticket_id.")
        return redirect('organizer_my_events')

    try:
        ticket = Ticket.objects.select_related("event", "user").get(ticket_id=ticket_id)
    except Ticket.DoesNotExist:
        messages.error(request, f"Ticket {ticket_id} not found.")
        return redirect('organizer_my_events')

    if ticket.event_id != event.id:
        messages.error(request, "This ticket is for a different event.")
        return redirect('organizer_my_events')

    # Validate using your existing business rules
    if ticket.is_valid():
        if ticket.status == Ticket.USED:
            messages.info(request, f"Ticket {ticket.ticket_id} was already used by {ticket.user.email}.")
        else:
            ticket.use_ticket()
            messages.success(
                request,
                f"Checked in: {ticket.user.get_full_name() or ticket.user.email} "
                f"(Ticket {ticket.ticket_id})"
            )
    else:
        # Build a reason (best-effort)
        reason = []
        if ticket.status == Ticket.CANCELLED:
            reason.append("cancelled")
        if ticket.status == Ticket.EXPIRED: 
            reason.append("expired")
        if ticket.event.status != Event.APPROVED:
            reason.append("event not approved")
        if ticket.expires_at and ticket.expires_at <= timezone.now():
            reason.append("expired")
        messages.error(request, f"Ticket invalid ({', '.join(reason) or 'not valid'}).")

    return redirect('organizer_my_events')

