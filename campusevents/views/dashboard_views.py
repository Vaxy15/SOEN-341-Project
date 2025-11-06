# campusevents/views/dashboard_views.py
"""
Admin dashboard and statistics views.
"""

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.shortcuts import render
from django.utils import timezone as dj_tz

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from ..models import User, Event, Ticket


class AdminDashboardStatsView(APIView):
    authentication_classes = (SessionAuthentication, JWTAuthentication)
    permission_classes = [IsAuthenticated]
    """
    Return summary statistics for admin dashboards.

    Response JSON:
    {
      "totals": {
        "total_users": int,
        "total_events": int,
        "tickets_issued_total": int,
        "tickets_used_total": int,
        "verified_organizers": int,
        "pending_organizers": int,
        "pending_events": int
      },
      "events_per_month": [ {"month": "YYYY-MM", "count": int}, ... ],   # last 12 months
      "tickets_per_month": [ {"month": "YYYY-MM", "issued": int, "used": int, "participation_rate": float}, ... ],
      "top_events_by_checkins": [ {"event_id": int, "title": str, "used": int}, ... ]  # top 5
    }
    """

    def get(self, request):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can view dashboard stats"}, status=status.HTTP_403_FORBIDDEN)

        # Totals
        total_users = User.objects.count()
        total_events = Event.objects.count()
        verified_organizers = User.objects.filter(role=User.ROLE_ORGANIZER, is_verified=True).count()
        pending_organizers = User.objects.filter(role=User.ROLE_ORGANIZER, is_verified=False).count()
        pending_events = Event.objects.filter(status=Event.PENDING).count()

        tickets_issued_total = Ticket.objects.filter(status=Ticket.ISSUED).count()
        tickets_used_total = Ticket.objects.filter(status=Ticket.USED).count()

        # Monthly buckets for the last 12 months (including current)
        now = dj_tz.now()

        # First day of this month at midnight
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        def month_start_n_ago(n: int):
            dt = first_of_this_month
            for _ in range(n):
                dt = (dt - timedelta(days=32)).replace(day=1)
            return dt

        events_per_month = []
        tickets_per_month = []

        # Build oldest → newest (11 months ago .. this month)
        for n in range(11, -1, -1):
            start = month_start_n_ago(n)
            next_month = (start + timedelta(days=32)).replace(day=1)
            ym = start.strftime('%Y-%m')

            # Events created in month
            events_count = Event.objects.filter(created_at__gte=start, created_at__lt=next_month).count()
            events_per_month.append({"month": ym, "count": events_count})

            # Tickets issued/used in month
            issued = Ticket.objects.filter(issued_at__gte=start, issued_at__lt=next_month).count()
            used = Ticket.objects.filter(used_at__isnull=False, used_at__gte=start, used_at__lt=next_month).count()
            participation_rate = float(used / issued) if issued else 0.0
            tickets_per_month.append({
                "month": ym,
                "issued": issued,
                "used": used,
                "participation_rate": round(participation_rate, 3),
            })

        # Top events by check-ins (used tickets)
        top_events_qs = (
            Event.objects
            .annotate(used_count=Count('tickets', filter=Q(tickets__status=Ticket.USED)))
            .order_by('-used_count', '-start_at')[:5]
        )
        top_events_by_checkins = [
            {"event_id": e.id, "title": e.title, "used": e.used_count or 0}
            for e in top_events_qs
        ]

        data = {
            "totals": {
                "total_users": total_users,
                "total_events": total_events,
                "tickets_issued_total": tickets_issued_total,
                "tickets_used_total": tickets_used_total,
                "verified_organizers": verified_organizers,
                "pending_organizers": pending_organizers,
                "pending_events": pending_events,
            },
            "events_per_month": events_per_month,
            "tickets_per_month": tickets_per_month,
            "top_events_by_checkins": top_events_by_checkins,
        }
        return Response(data)


@login_required(login_url='login')
def admin_dashboard_page(request):
    """
    Simple HTML page for administrators that fetches /admin/dashboard/stats/
    and renders global stats + participation trend.
    """
    if not getattr(request.user, 'is_admin', lambda: False)():
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Only administrators can view this page")

    return render(request, "admin_dashboard.html", {})

