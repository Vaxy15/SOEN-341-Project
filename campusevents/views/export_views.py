# campusevents/views/export_views.py
"""
CSV export views for event attendees.
"""

import csv

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Event


@login_required(login_url='login')
@require_GET
def event_attendees_csv(request, primary_key):
    """
    Plain Django view that returns attendees as CSV using SESSION auth.
    Only the event creator or an admin may download it.
    """
    event = get_object_or_404(Event, pk=primary_key)

    # allow: admins or the event creator
    if not (getattr(request.user, "is_admin", lambda: False)() or event.created_by_id == request.user.id):
        return HttpResponse("Forbidden", status=403)

    status_param = request.GET.get("status")
    tickets_qs = event.tickets.select_related("user").order_by("issued_at")
    if status_param:
        tickets_qs = tickets_qs.filter(status=status_param)

    filename = f"attendees_event_{event.id}.csv"
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "ticket_id","ticket_status","user_email","first_name","last_name",
        "student_id","phone_number","seat_number","issued_at","used_at"
    ])

    for t in tickets_qs:
        u = t.user
        writer.writerow([
            t.ticket_id,
            t.status,
            u.email or "",
            u.first_name or "",
            u.last_name or "",
            getattr(u, "student_id", "") or "",
            getattr(u, "phone_number", "") or "",
            t.seat_number or "",
            t.issued_at.isoformat() if t.issued_at else "",
            t.used_at.isoformat() if t.used_at else "",
        ])

    return response


class EventAttendeesCSVListView(APIView):
    """
    API version (JWT/DRF auth). In urls.py its name should be different from the
    session route to avoid reverse() collisions — e.g. 'event_attendees_csv_api'.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, primary_key):
        event = get_object_or_404(Event, pk=primary_key)

        if not (request.user.is_admin() or event.created_by == request.user):
            return Response({"error": "You do not have permission to download attendees for this event"}, status=status.HTTP_403_FORBIDDEN)

        status_param = request.query_params.get("status")
        tickets_qs = event.tickets.select_related("user").order_by("issued_at")
        if status_param:
            tickets_qs = tickets_qs.filter(status=status_param)

        filename = f"attendees_event_{event.id}.csv"
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(["ticket_id","ticket_status","user_email","first_name","last_name","student_id","phone_number","seat_number","issued_at","used_at"])

        for t in tickets_qs:
            u = t.user
            writer.writerow([
                t.ticket_id,
                t.status,
                u.email or "",
                u.first_name or "",
                u.last_name or "",
                getattr(u, "student_id", "") or "",
                getattr(u, "phone_number", "") or "",
                t.seat_number or "",
                t.issued_at.isoformat() if t.issued_at else "",
                t.used_at.isoformat() if t.used_at else "",
            ])

        return response

