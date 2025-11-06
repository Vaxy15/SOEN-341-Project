# campusevents/views/ticket_views.py
"""
Ticket management and validation views.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Event, Ticket
from ..serializers import TicketSerializer, TicketIssueSerializer, TicketValidationSerializer


class TicketIssueView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TicketIssueSerializer(data=request.data)
        if serializer.is_valid():
            event_id = serializer.validated_data["event_id"]
            event = Event.objects.get(id=event_id)
            existing_ticket = Ticket.objects.filter(event=event, user=request.user).first()
            if existing_ticket:
                return Response({"error": "You already have a ticket for this event"}, status=status.HTTP_400_BAD_REQUEST)
            ticket = Ticket.objects.create(
                event=event,
                user=request.user,
                seat_number=serializer.validated_data.get("seat_number", ""),
                notes=serializer.validated_data.get("notes", ""),
                expires_at=serializer.validated_data.get("expires_at"),
            )
            return Response(TicketSerializer(ticket).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TicketValidationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TicketValidationSerializer(data=request.data)
        if serializer.is_valid():
            ticket_id = serializer.validated_data["ticket_id"]
            try:
                ticket = Ticket.objects.get(ticket_id=ticket_id)
            except Ticket.DoesNotExist:
                return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

            if not (request.user.role in ["organizer", "admin"] or ticket.event.created_by == request.user):
                return Response({"error": "You do not have permission to validate this ticket"}, status=status.HTTP_403_FORBIDDEN)

            if ticket.is_valid():
                ticket.use_ticket()
                return Response({"valid": True, "ticket": TicketSerializer(ticket).data, "message": "Ticket validated and marked as used"}, status=status.HTTP_200_OK)
            else:
                return Response({"valid": False, "ticket": TicketSerializer(ticket).data, "message": "Ticket is not valid (expired, cancelled, or event not approved)"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyTicketsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tickets = Ticket.objects.filter(user=request.user).order_by("-issued_at")
        return Response(TicketSerializer(tickets, many=True).data)


class TicketDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Ticket.objects.get(pk=pk)
        except Ticket.DoesNotExist:
            return None

    def get(self, request, pk):
        ticket = self.get_object(pk)
        if ticket is None:
            return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)
        if not (ticket.user == request.user or request.user.role in ["admin", "organizer"]):
            return Response({"error": "You do not have permission to view this ticket"}, status=status.HTTP_403_FORBIDDEN)
        return Response(TicketSerializer(ticket).data)

    def delete(self, request, pk):
        ticket = self.get_object(pk)
        if ticket is None:
            return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)
        if not (ticket.user == request.user or request.user.role == "admin"):
            return Response({"error": "You do not have permission to cancel this ticket"}, status=status.HTTP_403_FORBIDDEN)
        if ticket.status == Ticket.USED:
            return Response({"error": "Cannot cancel a ticket that has already been used"}, status=status.HTTP_400_BAD_REQUEST)
        ticket.cancel_ticket()
        return Response({"message": "Ticket cancelled successfully"}, status=status.HTTP_200_OK)


@login_required(login_url='login')
@require_POST
def claim_ticket(request, pk):
    event = get_object_or_404(Event, pk=pk, status=Event.APPROVED)

    # Already has a ticket?
    if Ticket.objects.filter(event=event, user=request.user, status=Ticket.ISSUED).exists():
        messages.info(request, "You already claimed a ticket for this event.")
        return redirect(request.META.get("HTTP_REFERER", "event_list_page"))

    # Capacity check
    if event.capacity and event.remaining_capacity <= 0:
        messages.error(request, "This event is full.")
        return redirect(request.META.get("HTTP_REFERER", "event_list_page"))

    # (Optional) don't allow claims after event ends
    if event.end_at and event.end_at <= timezone.now():
        messages.error(request, "This event has already ended.")
        return redirect(request.META.get("HTTP_REFERER", "event_list_page"))

    # Create a ticket (defaults to status=ISSUED and generates QR)
    Ticket.objects.create(event=event, user=request.user)

    messages.success(request, "Ticket claimed successfully!")
    return redirect(request.META.get("HTTP_REFERER", "event_list_page"))


@login_required(login_url='login')
def my_events(request):
    """List all events for which the logged-in user has a ticket."""
    tickets = Ticket.objects.filter(user=request.user).select_related("event").order_by("-issued_at")

    context = {
        "tickets": tickets,
        "now": timezone.now(),
    }
    return render(request, "my_events.html", context)

