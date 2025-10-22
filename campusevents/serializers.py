# campusevents/serializers.py
"""
Serializers for the campusevents app.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils import timezone
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


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin user management with all fields."""

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role',
            'student_id', 'phone_number', 'date_of_birth',
            'is_verified', 'is_active', 'is_staff', 'is_superuser',
            'created_at', 'updated_at', 'last_login'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_login']


class UserApprovalSerializer(serializers.Serializer):
    """Serializer for user approval actions."""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate_action(self, value):
        """Validate action choice."""
        if value not in ['approve', 'reject']:
            raise serializers.ValidationError("Action must be 'approve' or 'reject'")
        return value


class UserRoleUpdateSerializer(serializers.Serializer):
    """Serializer for updating user roles."""
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)

    def validate_role(self, value):
        """Validate role choice."""
        if value not in [choice[0] for choice in User.ROLE_CHOICES]:
            raise serializers.ValidationError("Invalid role choice")
        return value


class UserStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating user status."""
    is_active = serializers.BooleanField()
    is_verified = serializers.BooleanField(required=False)


class AdminEventSerializer(serializers.ModelSerializer):
    """Serializer for admin event management with all fields."""

    org_name = serializers.CharField(source='org.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    remaining_capacity = serializers.ReadOnlyField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'category', 'location',
            'start_at', 'end_at', 'capacity', 'remaining_capacity',
            'ticket_type', 'status', 'admin_comment', 'org', 'org_name',
            'created_by', 'created_by_name', 'created_by_email'
        ]
        read_only_fields = ['id', 'created_by']


class EventApprovalSerializer(serializers.Serializer):
    """Serializer for event approval actions."""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    comment = serializers.CharField(required=False, allow_blank=True, help_text="Admin comment for rejection or approval")

    def validate_action(self, value):
        """Validate action choice."""
        if value not in ['approve', 'reject']:
            raise serializers.ValidationError("Action must be 'approve' or 'reject'")
        return value


class EventStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating event status."""
    status = serializers.ChoiceField(choices=Event.STATUS_CHOICES)
    comment = serializers.CharField(required=False, allow_blank=True, help_text="Admin comment for status change")

    def validate_status(self, value):
        """Validate status choice."""
        if value not in [choice[0] for choice in Event.STATUS_CHOICES]:
            raise serializers.ValidationError("Invalid status choice")
        return value


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

    def validate(self, attrs):
        """Validate event data."""
        start_at = attrs.get('start_at')
        end_at = attrs.get('end_at')

        # Validate end time is after start time
        if start_at and end_at and end_at <= start_at:
            raise serializers.ValidationError(
                "End time must be after start time."
            )

        # Validate start time is in the future (unless it's a draft)
        if start_at and start_at <= timezone.now() and attrs.get('status') != Event.DRAFT:
            raise serializers.ValidationError(
                "Start time must be in the future for non-draft events."
            )

        # Validate capacity is positive
        capacity = attrs.get('capacity', 0)
        if capacity < 0:
            raise serializers.ValidationError(
                "Capacity must be a positive number."
            )

        return attrs


class EventCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating events with enhanced validation."""

    class Meta:
        model = Event
        fields = [
            'title', 'description', 'category', 'location',
            'start_at', 'end_at', 'capacity', 'ticket_type', 'org', 'status'
        ]

    def validate(self, attrs):
        """Validate event creation data."""
        start_at = attrs.get('start_at')
        end_at = attrs.get('end_at')
        status = attrs.get('status', Event.PENDING)

        # Validate end time is after start time
        if start_at and end_at and end_at <= start_at:
            raise serializers.ValidationError(
                "End time must be after start time."
            )

        # Validate start time is in the future (unless it's a draft)
        if start_at and start_at <= timezone.now() and status != Event.DRAFT:
            raise serializers.ValidationError(
                "Start time must be in the future for non-draft events."
            )

        # Validate capacity is positive
        capacity = attrs.get('capacity', 0)
        if capacity < 0:
            raise serializers.ValidationError(
                "Capacity must be a positive number."
            )

        # Validate required fields for non-draft events
        if status != Event.DRAFT:
            required_fields = ['title', 'description', 'location', 'start_at', 'end_at']
            for field in required_fields:
                if not attrs.get(field):
                    raise serializers.ValidationError(
                        f"{field.replace('_', ' ').title()} is required for non-draft events."
                    )

        return attrs


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
