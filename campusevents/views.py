
"""
Views for the campusevents app.
"""

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from datetime import datetime
from .models import User, Organization, Event, Ticket
from .serializers import (
    CustomTokenObtainPairSerializer, UserSerializer, AdminUserSerializer, 
    UserApprovalSerializer, UserRoleUpdateSerializer, UserStatusUpdateSerializer,
    StudentRegistrationSerializer, OrganizerRegistrationSerializer, OrganizationSerializer, 
    EventSerializer, EventCreateSerializer, TicketSerializer, TicketIssueSerializer, 
    TicketValidationSerializer
)

class EventPagination(PageNumberPagination):
    """Custom pagination for events."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token view that includes user role information."""
    serializer_class = CustomTokenObtainPairSerializer
def home(request):
    events = Event.objects.all()
    return render(request, "home.html", {"events": events})

class UserProfileView(APIView):
    """View to get and update user profile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current user's profile."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        """Update current user's profile."""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRegistrationView(APIView):
    """View for user registration."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Register a new user."""
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Set password
            user.set_password(request.data.get('password'))
            user.save()

            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            return Response({
                'access': str(access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StudentRegistrationView(APIView):
    """View for student registration with specific validation."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Register a new student."""
        serializer = StudentRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            # Create user with password
            user = serializer.save()
            user.set_password(request.data.get('password'))
            user.save()

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            return Response({
                'message': 'Student registration successful',
                'access': str(access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'is_active': user.is_active,
                    'is_verified': user.is_verified
                }
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizerRegistrationView(APIView):
    """View for organizer registration requiring admin approval."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Register a new organizer (requires admin approval)."""
        serializer = OrganizerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            # Create user with password
            user = serializer.save()
            user.set_password(request.data.get('password'))
            user.save()

            # Return confirmation without JWT tokens (account inactive)
            return Response({
                'message': 'Organizer registration submitted successfully. Your account is pending admin approval.',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'is_active': user.is_active,
                    'is_verified': user.is_verified
                },
                'status': 'pending_approval',
                'note': 'You will be notified when your account is approved and you can start creating events.'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizationListView(APIView):  # pylint: disable=no-member
    """View to list and create organizations."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List all organizations."""
        organizations = Organization.objects.all()
        serializer = OrganizationSerializer(organizations, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new organization (admin only)."""
        if not request.user.role == 'admin':
            return Response(
                {'error': 'Only administrators can create organizations'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = OrganizationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventListView(APIView):  # pylint: disable=no-member
    """View to list and create events."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List all events."""
        events = Event.objects.all()
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new event (approved organizers and admins only)."""
        if not request.user.role in ['organizer', 'admin']:
            return Response(
                {'error': 'Only organizers and administrators can create events'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if organizer is approved (admins are always approved)
        if request.user.role == 'organizer' and not request.user.is_verified:
            return Response(
                {'error': 'Your organizer account is pending admin approval. You cannot create events until approved.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Determine event status based on request data
        event_status = request.data.get('status', Event.PENDING)
        
        # Validate status choice
        if event_status not in [Event.DRAFT, Event.PENDING]:
            return Response(
                {'error': 'Event status must be either "draft" or "pending"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = EventCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Set the status and created_by
            event = serializer.save(created_by=request.user, status=event_status)
            
            # Return the event with full details
            response_serializer = EventSerializer(event)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventDiscoveryView(APIView):
    """View for students to discover approved events with filtering and pagination."""
    permission_classes = [IsAuthenticated]
    pagination_class = EventPagination

    def get(self, request):
        """List approved events with filtering and pagination for students."""
        # Only show approved events
        events = Event.objects.filter(status=Event.APPROVED)
        
        # Apply filters
        category = request.query_params.get('category', None)
        organization = request.query_params.get('organization', None)
        date_from = request.query_params.get('date_from', None)
        date_to = request.query_params.get('date_to', None)
        search = request.query_params.get('search', None)
        
        if category:
            events = events.filter(category__icontains=category)
        
        if organization:
            events = events.filter(org__name__icontains=organization)
        
        if date_from:
            try:
                date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                events = events.filter(start_at__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                events = events.filter(start_at__lte=date_to_obj)
            except ValueError:
                pass
        
        if search:
            events = events.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) | 
                Q(location__icontains=search)
            )
        
        # Order by start date (upcoming events first)
        events = events.order_by('start_at')
        
        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(events, request)
        
        if page is not None:
            serializer = EventSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        # Fallback if pagination is not used
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)


class OrganizerEventManagementView(APIView):
    """View for organizers to manage their events including drafts."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get organizer's events including drafts."""
        if not request.user.role in ['organizer', 'admin']:
            return Response(
                {'error': 'Only organizers and administrators can manage events'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get events created by the current user
        events = Event.objects.filter(created_by=request.user).order_by('-created_at')
        
        # Apply status filter if provided
        status_filter = request.query_params.get('status', None)
        if status_filter:
            events = events.filter(status=status_filter)
        
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new event or draft (approved organizers and admins only)."""
        if not request.user.role in ['organizer', 'admin']:
            return Response(
                {'error': 'Only organizers and administrators can create events'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if organizer is approved (admins are always approved)
        if request.user.role == 'organizer' and not request.user.is_verified:
            return Response(
                {'error': 'Your organizer account is pending admin approval. You cannot create events until approved.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Determine event status based on request data
        event_status = request.data.get('status', Event.PENDING)
        
        # Validate status choice
        if event_status not in [Event.DRAFT, Event.PENDING]:
            return Response(
                {'error': 'Event status must be either "draft" or "pending"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = EventCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Set the status and created_by
            event = serializer.save(created_by=request.user, status=event_status)
            
            # Return the event with full details
            response_serializer = EventSerializer(event)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventDetailView(APIView):  # pylint: disable=no-member
    """View to get, update, or delete a specific event."""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        """Get event by ID."""
        try:
            return Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return None

    def get(self, request, pk):
        """Get event details."""
        event = self.get_object(pk)
        if event is None:
            return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = EventSerializer(event)
        return Response(serializer.data)

    def put(self, request, pk):
        """Update event (owner, organizer, or admin only)."""
        event = self.get_object(pk)
        if event is None:
            return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check permissions
        if not (event.created_by == request.user or request.user.role in ['organizer', 'admin']):
            return Response(
                {'error': 'You can only edit your own events'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = EventSerializer(event, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Delete event (owner or admin only)."""
        event = self.get_object(pk)
        if event is None:
            return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check permissions
        if not (event.created_by == request.user or request.user.role == 'admin'):
            return Response(
                {'error': 'You can only delete your own events'},
                status=status.HTTP_403_FORBIDDEN
            )

        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout view to blacklist refresh token."""
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
    except KeyError:
        return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


class TicketIssueView(APIView):
    """View to issue tickets for events."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Issue a ticket for an event."""
        serializer = TicketIssueSerializer(data=request.data)
        if serializer.is_valid():
            event_id = serializer.validated_data['event_id']
            event = Event.objects.get(id=event_id)
            
            # Check if user already has a ticket for this event
            existing_ticket = Ticket.objects.filter(event=event, user=request.user).first()
            if existing_ticket:
                return Response(
                    {'error': 'You already have a ticket for this event'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create ticket
            ticket_data = {
                'event': event,
                'user': request.user,
                'seat_number': serializer.validated_data.get('seat_number', ''),
                'notes': serializer.validated_data.get('notes', ''),
                'expires_at': serializer.validated_data.get('expires_at'),
            }
            
            ticket = Ticket.objects.create(**ticket_data)
            ticket_serializer = TicketSerializer(ticket)
            
            return Response(ticket_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TicketValidationView(APIView):
    """View to validate tickets."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Validate a ticket by ticket ID."""
        serializer = TicketValidationSerializer(data=request.data)
        if serializer.is_valid():
            ticket_id = serializer.validated_data['ticket_id']
            
            try:
                ticket = Ticket.objects.get(ticket_id=ticket_id)
                
                # Check if user has permission to validate (organizer or admin)
                if not (request.user.role in ['organizer', 'admin'] or ticket.event.created_by == request.user):
                    return Response(
                        {'error': 'You do not have permission to validate this ticket'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Validate ticket
                is_valid = ticket.is_valid()
                if is_valid:
                    # Mark ticket as used
                    ticket.use_ticket()
                    return Response({
                        'valid': True,
                        'ticket': TicketSerializer(ticket).data,
                        'message': 'Ticket validated and marked as used'
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'valid': False,
                        'ticket': TicketSerializer(ticket).data,
                        'message': 'Ticket is not valid (expired, cancelled, or event not approved)'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Ticket.DoesNotExist:
                return Response(
                    {'error': 'Ticket not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyTicketsView(APIView):
    """View to get user's tickets."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all tickets for the current user."""
        tickets = Ticket.objects.filter(user=request.user).order_by('-issued_at')
        serializer = TicketSerializer(tickets, many=True)
        return Response(serializer.data)


class TicketDetailView(APIView):
    """View to get, update, or cancel a specific ticket."""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        """Helper to get ticket object."""
        try:
            return Ticket.objects.get(pk=pk)
        except Ticket.DoesNotExist:
            return None

    def get(self, request, pk):
        """Get ticket details."""
        ticket = self.get_object(pk)
        if ticket is None:
            return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if user owns the ticket or is admin/organizer
        if not (ticket.user == request.user or request.user.role in ['admin', 'organizer']):
            return Response(
                {'error': 'You do not have permission to view this ticket'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = TicketSerializer(ticket)
        return Response(serializer.data)

    def delete(self, request, pk):
        """Cancel a ticket (only ticket owner or admin)."""
        ticket = self.get_object(pk)
        if ticket is None:
            return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if user owns the ticket or is admin
        if not (ticket.user == request.user or request.user.role == 'admin'):
            return Response(
                {'error': 'You do not have permission to cancel this ticket'},
                status=status.HTTP_403_FORBIDDEN
            )

        if ticket.status == Ticket.USED:
            return Response(
                {'error': 'Cannot cancel a ticket that has already been used'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ticket.cancel_ticket()
        return Response({'message': 'Ticket cancelled successfully'}, status=status.HTTP_200_OK)


class AdminUserManagementView(APIView):
    """View for admin user management."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all users with filtering and search."""
        # Check if user is admin
        if not request.user.is_admin():
            return Response(
                {'error': 'Only administrators can manage users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all users
        users = User.objects.all()
        
        # Apply filters
        role_filter = request.query_params.get('role', None)
        status_filter = request.query_params.get('status', None)
        search = request.query_params.get('search', None)
        verification_status = request.query_params.get('verification_status', None)
        
        if role_filter:
            users = users.filter(role=role_filter)
        
        if status_filter == 'active':
            users = users.filter(is_active=True)
        elif status_filter == 'inactive':
            users = users.filter(is_active=False)
        
        if verification_status == 'verified':
            users = users.filter(is_verified=True)
        elif verification_status == 'unverified':
            users = users.filter(is_verified=False)
        
        if search:
            users = users.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(student_id__icontains=search)
            )
        
        # Order by creation date (newest first)
        users = users.order_by('-created_at')
        
        # Apply pagination
        paginator = EventPagination()
        page = paginator.paginate_queryset(users, request)
        
        if page is not None:
            serializer = AdminUserSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        # Fallback if pagination is not used
        serializer = AdminUserSerializer(users, many=True)
        return Response(serializer.data)


class AdminUserDetailView(APIView):
    """View for admin to manage individual users."""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        """Get user by ID."""
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        """Get user details."""
        if not request.user.is_admin():
            return Response(
                {'error': 'Only administrators can view user details'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object(pk)
        if user is None:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AdminUserSerializer(user)
        return Response(serializer.data)

    def patch(self, request, pk):
        """Update user details."""
        if not request.user.is_admin():
            return Response(
                {'error': 'Only administrators can update users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object(pk)
        if user is None:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AdminUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserApprovalView(APIView):
    """View for admin to approve/reject users."""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        """Get user by ID."""
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def post(self, request, pk):
        """Approve or reject a user."""
        if not request.user.is_admin():
            return Response(
                {'error': 'Only administrators can approve/reject users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object(pk)
        if user is None:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UserApprovalSerializer(data=request.data)
        if serializer.is_valid():
            action = serializer.validated_data['action']
            reason = serializer.validated_data.get('reason', '')
            
            if action == 'approve':
                user.is_verified = True
                user.is_active = True
                user.save()
                message = f'User {user.email} has been approved successfully.'
            else:  # reject
                user.is_verified = False
                user.is_active = False
                user.save()
                message = f'User {user.email} has been rejected.'
            
            return Response({
                'message': message,
                'user': AdminUserSerializer(user).data,
                'reason': reason
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserRoleView(APIView):
    """View for admin to change user roles."""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        """Get user by ID."""
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def post(self, request, pk):
        """Change user role."""
        if not request.user.is_admin():
            return Response(
                {'error': 'Only administrators can change user roles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object(pk)
        if user is None:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UserRoleUpdateSerializer(data=request.data)
        if serializer.is_valid():
            new_role = serializer.validated_data['role']
            old_role = user.role
            user.role = new_role
            user.save()
            
            return Response({
                'message': f'User role changed from {old_role} to {new_role}',
                'user': AdminUserSerializer(user).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserStatusView(APIView):
    """View for admin to activate/deactivate users."""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        """Get user by ID."""
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def post(self, request, pk):
        """Activate or deactivate a user."""
        if not request.user.is_admin():
            return Response(
                {'error': 'Only administrators can change user status'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object(pk)
        if user is None:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UserStatusUpdateSerializer(data=request.data)
        if serializer.is_valid():
            is_active = serializer.validated_data['is_active']
            is_verified = serializer.validated_data.get('is_verified', user.is_verified)
            
            user.is_active = is_active
            user.is_verified = is_verified
            user.save()
            
            status_text = 'activated' if is_active else 'deactivated'
            return Response({
                'message': f'User {user.email} has been {status_text}',
                'user': AdminUserSerializer(user).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminPendingOrganizersView(APIView):
    """View for admin to see pending organizer registrations."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all pending organizer registrations."""
        if not request.user.is_admin():
            return Response(
                {'error': 'Only administrators can view pending organizers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get unverified organizers
        pending_organizers = User.objects.filter(
            role=User.ROLE_ORGANIZER,
            is_verified=False
        ).order_by('-created_at')
        
        serializer = AdminUserSerializer(pending_organizers, many=True)
        return Response({
            'pending_organizers': serializer.data,
            'count': pending_organizers.count()
        })
