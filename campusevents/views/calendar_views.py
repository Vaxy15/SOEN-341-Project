# campusevents/views/calendar_views.py
"""
Calendar and event feed views.
"""

from datetime import timedelta

from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone as dj_tz
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET

from ..models import Event


def calendar_page(request):
    """
    HTML page: renders a month/week/day calendar.
    Events are fetched via /api/calendar-events/ (see view below).
    """
    return render(request, "calendar.html")


@require_GET
def calendar_events_feed(request):
    """
    JSON feed for FullCalendar.

    FullCalendar calls with ?start=...&end=... (ISO8601). We return all APPROVED
    events that overlap that window. Anonymous access is fine here since it's just
    public event info.
    """
    start_param = request.GET.get("start")
    end_param = request.GET.get("end")

    # If FullCalendar didn't send a window, just show the next 60 days
    start_dt = parse_datetime(start_param) if start_param else dj_tz.now() - timedelta(days=1)
    end_dt = parse_datetime(end_param) if end_param else dj_tz.now() + timedelta(days=60)

    if start_dt and dj_tz.is_naive(start_dt):
        start_dt = dj_tz.make_aware(start_dt, dj_tz.get_current_timezone())
    if end_dt and dj_tz.is_naive(end_dt):
        end_dt = dj_tz.make_aware(end_dt, dj_tz.get_current_timezone())

    # Overlap query: (event.end >= window.start) & (event.start <= window.end)
    qs = (
        Event.objects
        .filter(status=Event.APPROVED, end_at__gte=start_dt, start_at__lte=end_dt)
        .select_related("org")
        .order_by("start_at")
    )

    # Build FullCalendar event dicts
    events = []
    for e in qs:
        events.append({
            "id": e.id,
            "title": e.title,
            "start": e.start_at.isoformat(),
            "end": e.end_at.isoformat() if e.end_at else None,
            "url": f"/events/?search={e.title}",
            "extendedProps": {
                "organization": e.org.name if e.org_id else "",
                "location": e.location or "",
                "category": e.category or "",
                "remaining": e.remaining_capacity,
            },
        })
    return JsonResponse(events, safe=False)

