"""
Serializers for the campusevents app.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Organization, Event, Ticket


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer that includes user role information."""

    def create(self, validated_data):
        """Create method required by BaseSerializer."""
        pass

    def update(self, instance, validated_data):
        """Update method required by BaseSerializer."""
        pass

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['email'] = user.email
        token['role'] = user.role
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['is_verified'] = user.is_verified

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add user information to the response
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'is_verified': self.user.is_verified,
            'student_id': self.user.student_id,
        }

        return data


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role',
            'student_id', 'phone_number', 'date_of_birth',
            'is_verified', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class StudentRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for student registration with validation."""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm', 'first_name', 'last_name', 'role'
        ]
        extra_kwargs = {
            'role': {'default': User.ROLE_STUDENT}
        }
    
    def validate_email(self, value):
        """Validate email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords do not match.")
        return attrs
    
    def create(self, validated_data):
        """Create a new student user."""
        # Remove password_confirm from validated_data
        validated_data.pop('password_confirm')
        
        # Ensure role is set to student
        validated_data['role'] = User.ROLE_STUDENT
        validated_data['is_active'] = True  # Student account is immediately active
        
        # Create user
        user = User.objects.create_user(**validated_data)
        return user


class OrganizerRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for organizer registration with admin approval workflow."""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm', 'first_name', 'last_name', 'role'
        ]
        extra_kwargs = {
            'role': {'default': User.ROLE_ORGANIZER}
        }
    
    def validate_email(self, value):
        """Validate email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords do not match.")
        return attrs
    
    def create(self, validated_data):
        """Create a new organizer user requiring admin approval."""
        # Remove password_confirm from validated_data
        validated_data.pop('password_confirm')
        
        # Ensure role is set to organizer
        validated_data['role'] = User.ROLE_ORGANIZER
        validated_data['is_active'] = False  # Account inactive until approved
        validated_data['is_verified'] = False  # Requires admin approval
        
        # Create user
        user = User.objects.create_user(**validated_data)
        return user


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model."""

    class Meta:
        model = Organization
        fields = ['id', 'name', 'description', 'approved']
        read_only_fields = ['id']


class EventSerializer(serializers.ModelSerializer):
    """Serializer for Event model."""

    org_name = serializers.CharField(source='org.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    remaining_capacity = serializers.ReadOnlyField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'category', 'location',
            'start_at', 'end_at', 'capacity', 'remaining_capacity',
            'ticket_type', 'status', 'org', 'org_name', 'created_by',
            'created_by_name'
        ]
        read_only_fields = ['id', 'created_by']


class TicketSerializer(serializers.ModelSerializer):
    """Serializer for Ticket model."""
    
    event_title = serializers.CharField(source='event.title', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    qr_code_url = serializers.ReadOnlyField()
    is_valid = serializers.ReadOnlyField()
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'ticket_id', 'event', 'event_title', 'user', 'user_name',
            'status', 'qr_code', 'qr_code_url', 'qr_code_data', 'issued_at',
            'used_at', 'expires_at', 'seat_number', 'notes', 'is_valid'
        ]
        read_only_fields = ['id', 'ticket_id', 'qr_code', 'qr_code_data', 'issued_at', 'used_at']


class TicketIssueSerializer(serializers.Serializer):
    """Serializer for issuing tickets."""
    
    event_id = serializers.IntegerField()
    seat_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    expires_at = serializers.DateTimeField(required=False)
    
    def validate_event_id(self, value):
        """Validate that the event exists and is approved."""
        try:
            event = Event.objects.get(id=value)
            if event.status != Event.APPROVED:
                raise serializers.ValidationError("Event is not approved for ticket issuance.")
            if event.remaining_capacity <= 0:
                raise serializers.ValidationError("Event is at full capacity.")
            return value
        except Event.DoesNotExist:
            raise serializers.ValidationError("Event does not exist.")


class TicketValidationSerializer(serializers.Serializer):
    """Serializer for validating tickets."""
    
    ticket_id = serializers.CharField(max_length=50)
    
    def validate_ticket_id(self, value):
        """Validate that the ticket exists."""
        try:
            ticket = Ticket.objects.get(ticket_id=value)
            return value
        except Ticket.DoesNotExist:
            raise serializers.ValidationError("Ticket does not exist.")
