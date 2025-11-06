# campusevents/views/admin_event_views.py
"""
Admin views for event moderation and approval.
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Event
from ..serializers import (
    AdminEventSerializer,
    EventApprovalSerializer,
    EventStatusUpdateSerializer,
)
from .utils import EventPagination


class AdminEventModerationView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = EventPagination

    def get(self, request):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can moderate events"}, status=status.HTTP_403_FORBIDDEN)

        events = Event.objects.all()

        status_filter = request.query_params.get("status")
        search = request.query_params.get("search")
        org_filter = request.query_params.get("organization")
        category_filter = request.query_params.get("category")

        if status_filter:
            events = events.filter(status=status_filter)
        if search:
            events = events.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(location__icontains=search)
                | Q(created_by__email__icontains=search)
            )
        if org_filter:
            events = events.filter(org__name__icontains=org_filter)
        if category_filter:
            events = events.filter(category__icontains=category_filter)

        events = events.select_related("org", "created_by")
        events = events.order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(events, request)
        serializer = AdminEventSerializer(page or events, many=True)
        if page is not None:
            return paginator.get_paginated_response(serializer.data)
        return Response(serializer.data)


class AdminEventDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return None

    def get(self, request, pk):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can view event details"}, status=status.HTTP_403_FORBIDDEN)
        event = self.get_object(pk)
        if event is None:
            return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminEventSerializer(event).data)

    def patch(self, request, pk):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can update events"}, status=status.HTTP_403_FORBIDDEN)
        event = self.get_object(pk)
        if event is None:
            return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminEventSerializer(event, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminEventApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return None

    def post(self, request, pk):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can approve/reject events"}, status=status.HTTP_403_FORBIDDEN)
        event = self.get_object(pk)
        if event is None:
            return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = EventApprovalSerializer(data=request.data)
        if serializer.is_valid():
            action = serializer.validated_data["action"]
            comment = serializer.validated_data.get("comment", "")
            if action == "approve":
                event.status = Event.APPROVED
                event.admin_comment = comment or None
                event.save()
                message = f'Event "{event.title}" has been approved successfully.'
            else:
                event.status = Event.REJECTED
                event.admin_comment = comment or "Event rejected by administrator"
                event.save()
                message = f'Event "{event.title}" has been rejected.'
            return Response({"message": message, "event": AdminEventSerializer(event).data, "comment": comment}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminEventStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return None

    def post(self, request, pk):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can change event status"}, status=status.HTTP_403_FORBIDDEN)
        event = self.get_object(pk)
        if event is None:
            return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = EventStatusUpdateSerializer(data=request.data)
        if serializer.is_valid():
            old_status = event.status
            event.status = serializer.validated_data["status"]
            comment = serializer.validated_data.get("comment", "")
            if comment:
                event.admin_comment = comment
            event.save()
            return Response({"message": f"Event status changed from {old_status} to {event.status}", "event": AdminEventSerializer(event).data, "comment": comment}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminPendingEventsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can view pending events"}, status=status.HTTP_403_FORBIDDEN)
        pending_events = Event.objects.filter(status=Event.PENDING).order_by("-created_at")
        return Response({"pending_events": AdminEventSerializer(pending_events, many=True).data, "count": pending_events.count()})


@login_required(login_url='login')
def admin_events_dashboard(request):
    """
    Simple HTML dashboard for administrators to browse and filter events.
    This page uses the API endpoint `/api/admin/events/` (or `/admin/events/` alias)
    and requires the user to be an admin.
    """
    if not getattr(request.user, 'is_admin', lambda: False)():
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Only administrators can view this page")

    return render(request, "admin_events_dashboard.html", {})

