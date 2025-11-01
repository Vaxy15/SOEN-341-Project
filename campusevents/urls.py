from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Login/logout (HTML)
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),  # uses LOGOUT_REDIRECT_URL

    # Register (HTML)
    path("register/", views.register_view, name="register"),

    # HTML pages
    path("", views.home, name="home"),
    path("events/", views.event_list_page, name="event_list_page"),
    path("events/create/", views.create_event, name="create_event"),
    path("events/<int:pk>/claim/", views.claim_ticket, name="claim_ticket"),
    path("events/confirmation/<int:pk>/", views.event_confirmation, name="event_confirmation"),
    path("my-events/", views.my_events, name="my_events"),
    path("calendar/", views.calendar_page, name="calendar_page"),

    # Calendar feed for FullCalendar
    path("api/calendar-events/", views.calendar_events_feed, name="calendar_events_feed"),

    # API endpoints
    path("api/profile/", views.UserProfileView.as_view(), name="user_profile"),
    path("api/register/", views.UserRegistrationView.as_view(), name="user_registration"),
    path("api/register/student/", views.StudentRegistrationView.as_view(), name="student_registration"),
    path("api/register/organizer/", views.OrganizerRegistrationView.as_view(), name="organizer_registration"),
    path("api/organizations/", views.OrganizationListView.as_view(), name="organization_list"),
    path("api/events/", views.EventListView.as_view(), name="event_list"),
    path("api/events/discover/", views.EventDiscoveryView.as_view(), name="event_discovery"),
    path("api/events/<int:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path("api/events/<int:primary_key>/attendees/csv/", views.EventAttendeesCSVListView.as_view(), name="event_attendees_csv"),
    path("api/tickets/issue/", views.TicketIssueView.as_view(), name="ticket_issue"),
    path("api/tickets/validate/", views.TicketValidationView.as_view(), name="ticket_validate"),
    path("api/tickets/my-tickets/", views.MyTicketsView.as_view(), name="my_tickets"),
    path("api/tickets/<int:pk>/", views.TicketDetailView.as_view(), name="ticket_detail"),
    path("api/logout/", views.logout_view, name="api_logout"),

    # Admin endpoints
    path("api/admin/users/", views.AdminUserManagementView.as_view(), name="admin_users"),
    path("api/admin/users/<int:pk>/", views.AdminUserDetailView.as_view(), name="admin_user_detail"),
    path("api/admin/users/<int:pk>/approve/", views.AdminUserApprovalView.as_view(), name="admin_user_approval"),
    path("api/admin/users/<int:pk>/role/", views.AdminUserRoleView.as_view(), name="admin_user_role"),
    path("api/admin/users/<int:pk>/status/", views.AdminUserStatusView.as_view(), name="admin_user_status"),
    path("api/admin/pending-organizers/", views.AdminPendingOrganizersView.as_view(), name="admin_pending_organizers"),
    path("api/admin/events/", views.AdminEventModerationView.as_view(), name="admin_events"),
    path("api/admin/events/<int:pk>/", views.AdminEventDetailView.as_view(), name="admin_event_detail"),
    path("api/admin/events/<int:pk>/approve/", views.AdminEventApprovalView.as_view(), name="admin_event_approval"),
    path("api/admin/events/<int:pk>/status/", views.AdminEventStatusView.as_view(), name="admin_event_status"),
    path("api/admin/pending-events/", views.AdminPendingEventsView.as_view(), name="admin_pending_events"),

    # Alias routes for approval (added to match docs / alternate clients)
    path("api/admin/events/<int:pk>/approval/", views.AdminEventApprovalView.as_view(), name="admin_event_approval_api_alias"),
    path("admin/events/<int:pk>/approval/", views.AdminEventApprovalView.as_view(), name="admin_event_approval_alias"),
]
