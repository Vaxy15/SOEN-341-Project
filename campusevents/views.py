
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
from .models import Organization, Event, Ticket
from .serializers import (
    CustomTokenObtainPairSerializer, UserSerializer, StudentRegistrationSerializer, 
    OrganizationSerializer, EventSerializer, TicketSerializer, TicketIssueSerializer, 
    TicketValidationSerializer
)

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
        """Create a new event (organizers and admins only)."""
        if not request.user.role in ['organizer', 'admin']:
            return Response(
                {'error': 'Only organizers and administrators can create events'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = EventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
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
