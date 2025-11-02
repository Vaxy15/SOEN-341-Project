# campusevents/views.py
"""
Views for the campusevents app.
"""

from datetime import datetime
import csv
import json

import numpy as np
import cv2

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication


from .models import User, Organization, Event, Ticket
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer,
    AdminUserSerializer,
    UserApprovalSerializer,
    UserRoleUpdateSerializer,
    UserStatusUpdateSerializer,
    StudentRegistrationSerializer,
    OrganizerRegistrationSerializer,
    OrganizationSerializer,
    EventSerializer,
    EventCreateSerializer,
    AdminEventSerializer,
    EventApprovalSerializer,
    EventStatusUpdateSerializer,
    TicketSerializer,
    TicketIssueSerializer,
    TicketValidationSerializer,
)


def build_event_discovery_qs(request):
    qs = (
        Event.objects
        .filter(status=Event.APPROVED, end_at__gte=timezone.now())
        .select_related("org")
        .order_by("start_at")
    )

    get_param = getattr(request, "query_params", request.GET)
    category = get_param.get("category")
    organization = get_param.get("organization")
    date_from = get_param.get("date_from")
    date_to = get_param.get("date_to")
    search = get_param.get("search")

    def parse_date(dt):
        try:
            return datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return None

    if category:
        qs = qs.filter(category__icontains=category)
    if organization:
        qs = qs.filter(org__name__icontains=organization)
    if date_from and (df := parse_date(date_from)):
        qs = qs.filter(start_at__gte=df)
    if date_to and (dtv := parse_date(date_to)):
        qs = qs.filter(start_at__lte=dtv)
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(location__icontains=search)
        )
    return qs


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


class EventPagination(PageNumberPagination):
    """Custom pagination for events."""
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token view that includes user role information."""
    serializer_class = CustomTokenObtainPairSerializer


def home(request):
    events = Event.objects.all()
    return render(request, "home.html", {"events": events})


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(request.data.get("password"))
            user.save()
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            return Response(
                {"access": str(access_token), "refresh": str(refresh), "user": UserSerializer(user).data},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StudentRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StudentRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(request.data.get("password"))
            user.save()
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            return Response(
                {
                    "message": "Student registration successful",
                    "access": str(access_token),
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "role": user.role,
                        "is_active": user.is_active,
                        "is_verified": user.is_verified,
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizerRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OrganizerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(request.data.get("password"))
            user.role = User.ROLE_ORGANIZER
            # Require approval:
            user.is_active = False
            user.is_verified = False
            user.save()
            return Response(
                {
                    "message": "Organizer registration submitted. Pending admin approval.",
                    "status": "pending_approval",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "role": user.role,
                        "is_active": user.is_active,
                        "is_verified": user.is_verified,
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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


class OrganizationListView(APIView):
    """List all organizations and allow admins to create new ones."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orgs = Organization.objects.all()
        serializer = OrganizationSerializer(orgs, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Only administrators can create organizations
        if not getattr(request.user, "role", None) == "admin":
            return Response(
                {"error": "Only administrators can create organizations"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OrganizationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
    except KeyError:
        return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)


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


class AdminUserManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can manage users"}, status=status.HTTP_403_FORBIDDEN)
        users = User.objects.all()
        role_filter = request.query_params.get("role")
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search")
        verification_status = request.query_params.get("verification_status")

        if role_filter:
            users = users.filter(role=role_filter)
        if status_filter == "active":
            users = users.filter(is_active=True)
        elif status_filter == "inactive":
            users = users.filter(is_active=False)
        if verification_status == "verified":
            users = users.filter(is_verified=True)
        elif verification_status == "unverified":
            users = users.filter(is_verified=False)
        if search:
            users = users.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(student_id__icontains=search)
            )

        users = users.order_by("-created_at")
        paginator = EventPagination()
        page = paginator.paginate_queryset(users, request)
        if page is not None:
            return paginator.get_paginated_response(AdminUserSerializer(page, many=True).data)
        return Response(AdminUserSerializer(users, many=True).data)


class AdminUserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can view user details"}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object(pk)
        if user is None:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminUserSerializer(user).data)

    def patch(self, request, pk):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can update users"}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object(pk)
        if user is None:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def post(self, request, pk):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can approve/reject users"}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object(pk)
        if user is None:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserApprovalSerializer(data=request.data)
        if serializer.is_valid():
            action = serializer.validated_data["action"]
            reason = serializer.validated_data.get("reason", "")
            if action == "approve":
                user.is_verified = True
                user.is_active = True
                user.save()
                message = f"User {user.email} has been approved successfully."
            else:
                user.is_verified = False
                user.is_active = False
                user.save()
                message = f"User {user.email} has been rejected."
            return Response({"message": message, "user": AdminUserSerializer(user).data, "reason": reason}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def post(self, request, pk):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can change user roles"}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object(pk)
        if user is None:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserRoleUpdateSerializer(data=request.data)
        if serializer.is_valid():
            old_role = user.role
            user.role = serializer.validated_data["role"]
            user.save()
            return Response({"message": f"User role changed from {old_role} to {user.role}", "user": AdminUserSerializer(user).data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def post(self, request, pk):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can change user status"}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object(pk)
        if user is None:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserStatusUpdateSerializer(data=request.data)
        if serializer.is_valid():
            user.is_active = serializer.validated_data["is_active"]
            user.is_verified = serializer.validated_data.get("is_verified", user.is_verified)
            user.save()
            status_text = "activated" if user.is_active else "deactivated"
            return Response({"message": f"User {user.email} has been {status_text}", "user": AdminUserSerializer(user).data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminPendingOrganizersView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = EventPagination

    def get(self, request):
        if not request.user.is_admin():
            return Response(
                {"error": "Only administrators can view pending organizers"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get unverified organizers
        pending_organizers = User.objects.filter(
            role=User.ROLE_ORGANIZER, is_verified=False
        ).order_by("-created_at")

        # Apply search filter
        search = request.query_params.get("search")
        if search:
            pending_organizers = pending_organizers.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        # Paginate results
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(pending_organizers, request)

        serializer = AdminUserSerializer(page or pending_organizers, many=True)

        if page is not None:
            return paginator.get_paginated_response(serializer.data)

        return Response(serializer.data)


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


# ---------- CSV EXPORTS ----------

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


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.method == "POST":
        role = (request.POST.get("role") or "").strip().lower()

        payload = {
            "email": (request.POST.get("email") or "").strip(),
            "password": request.POST.get("password") or "",
            "password_confirm": request.POST.get("password_confirm") or "",
            "first_name": (request.POST.get("first_name") or "").strip(),
            "last_name": (request.POST.get("last_name") or "").strip(),
            "student_id": (request.POST.get("student_id") or "").strip(),
            "phone_number": (request.POST.get("phone_number") or "").strip(),
        }

        # Pick the right serializer based on role
        if role == User.ROLE_STUDENT:
            serializer = StudentRegistrationSerializer(data=payload)
            role_label = "Student"
        elif role == User.ROLE_ORGANIZER:
            serializer = OrganizerRegistrationSerializer(data=payload)
            role_label = "Event Organizer"
        else:
            messages.error(request, "Please choose a valid account type (Student or Organizer).")
            return render(request, "register.html", {"form": request.POST}, status=400)

        if serializer.is_valid():
            user = serializer.save()
            user.set_password(payload["password"])
            user.role = role

            if role == User.ROLE_STUDENT:
                # Students: usable immediately
                user.is_active = True
                user.is_verified = True
                success_msg = f"{role_label} account created! You can sign in now."
            else:
                # Organizers: require admin approval
                user.is_active = False
                user.is_verified = True
                success_msg = (
                    f"{role_label} registration submitted. "
                    "An administrator must approve your account before you can sign in."
                )

            user.save()
            messages.success(request, success_msg)
            return redirect("login")

        # Validation errors
        return render(
            request,
            "register.html",
            {"form": request.POST, "errors": serializer.errors},
            status=400,
        )

    # GET
    return render(request, "register.html")


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

    # (Optional) don’t allow claims after event ends
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
    events that overlap that window. Anonymous access is fine here since it’s just
    public event info.
    """
    start_param = request.GET.get("start")
    end_param = request.GET.get("end")

    # If FullCalendar didn’t send a window, just show the next 60 days
    from django.utils import timezone as dj_tz
    from datetime import timedelta
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


@login_required(login_url='login')
def admin_users_dashboard(request):
    """
    Simple HTML page for administrators to list users and perform basic actions:
    - Change role (student / organizer / admin)
    - Toggle active status
    """
    if not getattr(request.user, 'is_admin', lambda: False)():
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Only administrators can view this page")

    users = User.objects.all().order_by('-created_at')[:200]
    return render(request, "admin_users_dashboard.html", {"users": users})


def _decode_qr_from_uploaded(django_file) -> str | None:
    """
    Try to decode a QR code from an uploaded image.
    Returns the decoded string (payload) or None.
    """
    data = django_file.read()
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    detector = cv2.QRCodeDetector()
    text, points, _ = detector.detectAndDecode(img)
    return text.strip() if text else None


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
        payload = _decode_qr_from_uploaded(uploaded)
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
        messages.error(request, "QR code doesn’t include a ticket_id.")
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
        if ticket.status == Ticket.CANCELLED: reason.append("cancelled")
        if ticket.status == Ticket.EXPIRED:   reason.append("expired")
        if ticket.event.status != Event.APPROVED: reason.append("event not approved")
        if ticket.expires_at and ticket.expires_at <= timezone.now(): reason.append("expired")
        messages.error(request, f"Ticket invalid ({', '.join(reason) or 'not valid'}).")

    return redirect('organizer_my_events')

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
        from django.utils import timezone as dj_tz
        from datetime import timedelta
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