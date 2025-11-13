# campusevents/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from campusevents.views import email_views  # add this


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
    path("organizer/my-events/", views.organizer_my_events, name="organizer_my_events"),
    path("organizer/events/<int:pk>/scan-ticket/", views.scan_ticket_image, name="scan_ticket_image"),
    path(
        "organizer/events/<int:primary_key>/attendees/export/",
        views.event_attendees_csv,
        name="event_attendees_csv",
    ),

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
    path(
        "api/events/<int:primary_key>/attendees/csv/",
        views.EventAttendeesCSVListView.as_view(),
        name="event_attendees_csv_api",  # fixed name to avoid clash
    ),
    path("api/tickets/issue/", views.TicketIssueView.as_view(), name="ticket_issue"),
    path("api/tickets/validate/", views.TicketValidationView.as_view(), name="ticket_validate"),
    path("api/tickets/my-tickets/", views.MyTicketsView.as_view(), name="my_tickets"),
    path("api/tickets/<int:pk>/", views.TicketDetailView.as_view(), name="ticket_detail"),
    path("api/logout/", views.logout_view, name="api_logout"),

    # ---------- DASHBOARD ROUTES (formerly "admin") ----------
    # These routes provide management pages and stats for site admins.

    # Dashboard overview page + stats API
    path("dashboard/", views.admin_dashboard_page, name="admin_dashboard_page"),
    path("dashboard/stats/", views.AdminDashboardStatsView.as_view(), name="admin_dashboard_stats"),
    path("api/dashboard/stats/", views.AdminDashboardStatsView.as_view(), name="admin_dashboard_stats_api"),
    # Convenience (no trailing slash)
    path("dashboard", views.admin_dashboard_page),
    path("dashboard/stats", views.AdminDashboardStatsView.as_view()),

    # User management
    path("dashboard/users/", views.AdminUserManagementView.as_view(), name="dashboard_users"),
    path("dashboard/users/<int:pk>/", views.AdminUserDetailView.as_view(), name="dashboard_user_detail"),
    path("dashboard/users/<int:pk>/approve/", views.AdminUserApprovalView.as_view(), name="dashboard_user_approval"),
    path("dashboard/users/<int:pk>/role/", views.AdminUserRoleView.as_view(), name="dashboard_user_role"),
    path("dashboard/users/<int:pk>/status/", views.AdminUserStatusView.as_view(), name="dashboard_user_status"),
    path("dashboard/pending-organizers/", views.AdminPendingOrganizersView.as_view(), name="dashboard_pending_organizers"),
    path("dashboard/users/dashboard/", views.admin_users_dashboard, name="dashboard_users_dashboard"),

    # Event management (moderation)
    path("dashboard/events/", views.AdminEventModerationView.as_view(), name="dashboard_events"),
    path("dashboard/events/<int:pk>/", views.AdminEventDetailView.as_view(), name="dashboard_event_detail"),
    path("dashboard/events/<int:pk>/approve/", views.AdminEventApprovalView.as_view(), name="dashboard_event_approval"),
    path("dashboard/events/<int:pk>/status/", views.AdminEventStatusView.as_view(), name="dashboard_event_status"),
    path("dashboard/pending-events/", views.AdminPendingEventsView.as_view(), name="dashboard_pending_events"),
    path("dashboard/events/dashboard/", views.admin_events_dashboard, name="dashboard_events_dashboard"),
    
    # Event attendees CSV export
    path(
        "dashboard/events/<int:primary_key>/attendees/export/",
        views.EventAttendeesCSVListView.as_view(),
        name="dashboard_event_attendees_csv",
    ),
    path("tickets/<int:pk>/resend-confirmation/", email_views.resend_confirmation, name="resend_confirmation"),
    path("tickets/view/", email_views.view_ticket_signed, name="view_ticket_signed"),
    path("dev/email/preview/claim/<int:pk>/", email_views.preview_claim_email, name="preview_claim_email"),




    # ---------- END DASHBOARD ROUTES ----------
]
