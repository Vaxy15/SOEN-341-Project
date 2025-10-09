from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),

    # API endpoints
    path('api/profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('api/register/', views.UserRegistrationView.as_view(), name='user_registration'),
    path('api/register/student/', views.StudentRegistrationView.as_view(), name='student_registration'),
    path('api/organizations/', views.OrganizationListView.as_view(), name='organization_list'),
    path('api/events/', views.EventListView.as_view(), name='event_list'),
    path('api/events/<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('api/logout/', views.logout_view, name='logout'),
    
    # Ticket endpoints
    path('api/tickets/issue/', views.TicketIssueView.as_view(), name='ticket_issue'),
    path('api/tickets/validate/', views.TicketValidationView.as_view(), name='ticket_validate'),
    path('api/tickets/my-tickets/', views.MyTicketsView.as_view(), name='my_tickets'),
    path('api/tickets/<int:pk>/', views.TicketDetailView.as_view(), name='ticket_detail'),
]
