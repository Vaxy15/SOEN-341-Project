# campusevents/views/__init__.py
"""
Views package for campusevents app.
Re-exports all views from organized submodules.
"""

# Utilities and pagination
from .utils import EventPagination, build_event_discovery_qs, decode_qr_from_uploaded

# Authentication views
from .auth_views import (
    CustomTokenObtainPairView,
    UserRegistrationView,
    StudentRegistrationView,
    OrganizerRegistrationView,
    register_view,
    logout_view,
)

# User views
from .user_views import UserProfileView

# Organization views
from .organization_views import OrganizationListView

# Event views
from .event_views import (
    home,
    event_list_page,
    create_event,
    event_confirmation,
    EventListView,
    EventDiscoveryView,
    EventDetailView,
    OrganizerEventManagementView,
)

# Ticket views
from .ticket_views import (
    TicketIssueView,
    TicketValidationView,
    MyTicketsView,
    TicketDetailView,
    claim_ticket,
    my_events,
)

# Admin user management views
from .admin_user_views import (
    AdminUserManagementView,
    AdminUserDetailView,
    AdminUserApprovalView,
    AdminUserRoleView,
    AdminUserStatusView,
    AdminPendingOrganizersView,
    admin_users_dashboard,
)

# Admin event management views
from .admin_event_views import (
    AdminEventModerationView,
    AdminEventDetailView,
    AdminEventApprovalView,
    AdminEventStatusView,
    AdminPendingEventsView,
    admin_events_dashboard,
)

# Dashboard views
from .dashboard_views import (
    AdminDashboardStatsView,
    admin_dashboard_page,
)

# Calendar views
from .calendar_views import (
    calendar_page,
    calendar_events_feed,
)

# Export views
from .export_views import (
    event_attendees_csv,
    EventAttendeesCSVListView,
)

# Organizer views
from .organizer_views import (
    organizer_my_events,
    scan_ticket_image,
)


__all__ = [
    # Utilities
    'EventPagination',
    'build_event_discovery_qs',
    'decode_qr_from_uploaded',
    
    # Authentication
    'CustomTokenObtainPairView',
    'UserRegistrationView',
    'StudentRegistrationView',
    'OrganizerRegistrationView',
    'register_view',
    'logout_view',
    
    # User
    'UserProfileView',
    
    # Organization
    'OrganizationListView',
    
    # Events
    'home',
    'event_list_page',
    'create_event',
    'event_confirmation',
    'EventListView',
    'EventDiscoveryView',
    'EventDetailView',
    'OrganizerEventManagementView',
    
    # Tickets
    'TicketIssueView',
    'TicketValidationView',
    'MyTicketsView',
    'TicketDetailView',
    'claim_ticket',
    'my_events',
    
    # Admin User Management
    'AdminUserManagementView',
    'AdminUserDetailView',
    'AdminUserApprovalView',
    'AdminUserRoleView',
    'AdminUserStatusView',
    'AdminPendingOrganizersView',
    'admin_users_dashboard',
    
    # Admin Event Management
    'AdminEventModerationView',
    'AdminEventDetailView',
    'AdminEventApprovalView',
    'AdminEventStatusView',
    'AdminPendingEventsView',
    'admin_events_dashboard',
    
    # Dashboard
    'AdminDashboardStatsView',
    'admin_dashboard_page',
    
    # Calendar
    'calendar_page',
    'calendar_events_feed',
    
    # Export
    'event_attendees_csv',
    'EventAttendeesCSVListView',
    
    # Organizer
    'organizer_my_events',
    'scan_ticket_image',
]

