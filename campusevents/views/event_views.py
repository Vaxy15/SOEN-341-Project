# campusevents/views/event_views.py
"""
Event management and discovery views.
"""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Event, Organization, Ticket
from ..api.serializers import EventSerializer, EventCreateSerializer
from .utils import build_event_discovery_qs, EventPagination


def home(request):
    events = Event.objects.all()
    return render(request, "home.html", {"events": events})


def event_list_page(request):
    qs = build_event_discovery_qs(request)
    page_size = int(request.GET.get("page_size", 10))
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(request.GET.get("page"))

    my_ticket_ids = set()
    if request.user.is_authenticated:
        page_event_ids = [e.id for e in page_obj.object_list]
        my_ticket_ids = set(
            Ticket.objects.filter(
                user=request.user,
                event_id__in=page_event_ids,
                status=Ticket.ISSUED,
            ).values_list("event_id", flat=True)
        )

    context = {
        "page_obj": page_obj,
        "filters": {
            "search": request.GET.get("search", ""),
            "category": request.GET.get("category", ""),
            "organization": request.GET.get("organization", ""),
            "date_from": request.GET.get("date_from", ""),
            "date_to": request.GET.get("date_to", ""),
            "page_size": page_size,
        },
        "page_sizes": [5, 10, 20, 50, 100],
        "my_ticket_ids": my_ticket_ids,
    }
    return render(request, "event_list.html", context)


@login_required(login_url='login')
def create_event(request):
    # Only organizers/admins can access the create page (redirect others to Discover)
    if request.user.role not in ['organizer', 'admin']:
        return redirect('event_list_page')

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        category = request.POST.get("category") or ""
        location = request.POST.get("location")
        start_at = request.POST.get("start_at")
        end_at = request.POST.get("end_at")
        capacity = request.POST.get("capacity") or 0
        ticket_type = request.POST.get("ticket_type") or "free"

        # ✅ Auto-approve for organizers/admins
        status_val = Event.APPROVED

        default_org, _ = Organization.objects.get_or_create(name="Default Org")

        event = Event.objects.create(
            title=title,
            description=description,
            category=category,
            location=location,
            start_at=start_at,
            end_at=end_at,
            capacity=capacity,
            ticket_type=ticket_type,
            status=status_val,
            created_by=request.user,
            org=default_org,
        )
        return redirect('event_confirmation', pk=event.pk)

    return render(request, "create_event.html")


def event_confirmation(request, pk):
    event = get_object_or_404(Event, pk=pk)
    return render(request, "event_confirmation.html", {"event": event})


class EventListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        events = Event.objects.all()
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Only organizers and admins can create events
        if request.user.role not in ["organizer", "admin"]:
            return Response(
                {"error": "Only organizers and administrators can create events"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = EventCreateSerializer(data=request.data)
        if serializer.is_valid():
            event = serializer.save(created_by=request.user, status=Event.APPROVED)
            return Response(EventSerializer(event).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventDiscoveryView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = EventPagination

    def get(self, request):
        events = build_event_discovery_qs(request)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(events, request)
        serializer = EventSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class EventDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return None

    def get(self, request, pk):
        event = self.get_object(pk)
        if event is None:
            return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(EventSerializer(event).data)

    def put(self, request, pk):
        event = self.get_object(pk)
        if event is None:
            return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)
        if not (event.created_by == request.user or request.user.role in ["organizer", "admin"]):
            return Response({"error": "You can only edit your own events"}, status=status.HTTP_403_FORBIDDEN)
        serializer = EventSerializer(event, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        event = self.get_object(pk)
        if event is None:
            return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)
        if not (event.created_by == request.user or request.user.role == "admin"):
            return Response({"error": "You can only delete your own events"}, status=status.HTTP_403_FORBIDDEN)
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizerEventManagementView(APIView):
    """
    Organizer dashboard: list your events and create new ones.
    Creation is auto-approved for organizers/admins to match your current rules.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ["organizer", "admin"]:
            return Response({"error": "Only organizers and administrators can manage events"},
                            status=status.HTTP_403_FORBIDDEN)
        events = Event.objects.filter(created_by=request.user).order_by("-created_at")
        return Response(EventSerializer(events, many=True).data)

    def post(self, request):
        if request.user.role not in ["organizer", "admin"]:
            return Response({"error": "Only organizers and administrators can create events"},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = EventCreateSerializer(data=request.data)
        if serializer.is_valid():
            event = serializer.save(created_by=request.user, status=Event.APPROVED)
            return Response(EventSerializer(event).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

