from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),

    # API endpoints
    path('api/profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('api/register/', views.UserRegistrationView.as_view(), name='user_registration'),
    path('api/register/student/', views.StudentRegistrationView.as_view(), name='student_registration'),
    path('api/register/organizer/', views.OrganizerRegistrationView.as_view(), name='organizer_registration'),
    path('api/organizations/', views.OrganizationListView.as_view(), name='organization_list'),
    path('api/events/', views.EventListView.as_view(), name='event_list'),
    path('api/events/discover/', views.EventDiscoveryView.as_view(), name='event_discovery'),
    path('api/events/my-events/', views.OrganizerEventManagementView.as_view(), name='organizer_events'),
    path('api/events/<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('api/logout/', views.logout_view, name='logout'),

    # Ticket endpoints
    path('api/tickets/issue/', views.TicketIssueView.as_view(), name='ticket_issue'),
    path('api/tickets/validate/', views.TicketValidationView.as_view(), name='ticket_validate'),
    path('api/tickets/my-tickets/', views.MyTicketsView.as_view(), name='my_tickets'),
    path('api/tickets/<int:pk>/', views.TicketDetailView.as_view(), name='ticket_detail'),

    # Admin user management endpoints
    path('api/admin/users/', views.AdminUserManagementView.as_view(), name='admin_users'),
    path('api/admin/users/<int:pk>/', views.AdminUserDetailView.as_view(), name='admin_user_detail'),
    path('api/admin/users/<int:pk>/approve/', views.AdminUserApprovalView.as_view(), name='admin_user_approval'),
    path('api/admin/users/<int:pk>/role/', views.AdminUserRoleView.as_view(), name='admin_user_role'),
    path('api/admin/users/<int:pk>/status/', views.AdminUserStatusView.as_view(), name='admin_user_status'),
    path('api/admin/pending-organizers/', views.AdminPendingOrganizersView.as_view(), name='admin_pending_organizers'),

    # Admin event moderation endpoints
    path('api/admin/events/', views.AdminEventModerationView.as_view(), name='admin_events'),
    path('api/admin/events/<int:pk>/', views.AdminEventDetailView.as_view(), name='admin_event_detail'),
    path('api/admin/events/<int:pk>/approve/', views.AdminEventApprovalView.as_view(), name='admin_event_approval'),
    path('api/admin/events/<int:pk>/status/', views.AdminEventStatusView.as_view(), name='admin_event_status'),
    path('api/admin/pending-events/', views.AdminPendingEventsView.as_view(), name='admin_pending_events'),
]
