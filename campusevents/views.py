
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
from .models import Organization, Event
from .serializers import CustomTokenObtainPairSerializer, UserSerializer, OrganizationSerializer, EventSerializer

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
