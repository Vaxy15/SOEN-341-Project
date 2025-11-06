# Views Module Structure

This folder contains the refactored views from the original monolithic `views.py` file (1343 lines) into organized, maintainable modules.

## File Organization

### Core Utilities
- **`utils.py`** (~80 lines)
  - `EventPagination` - Custom pagination class
  - `build_event_discovery_qs()` - Event filtering helper
  - `decode_qr_from_uploaded()` - QR code decoder utility

### Authentication & Registration
- **`auth_views.py`** (~180 lines)
  - `CustomTokenObtainPairView` - JWT token generation
  - `UserRegistrationView` - Generic user registration API
  - `StudentRegistrationView` - Student registration API
  - `OrganizerRegistrationView` - Organizer registration API
  - `register_view()` - HTML registration page
  - `logout_view()` - JWT logout endpoint

### User Management
- **`user_views.py`** (~25 lines)
  - `UserProfileView` - User profile GET/PATCH

### Organization Management
- **`organization_views.py`** (~40 lines)
  - `OrganizationListView` - List/create organizations

### Event Management
- **`event_views.py`** (~210 lines)
  - `home()` - Home page
  - `event_list_page()` - Event listing HTML page
  - `create_event()` - Event creation HTML page
  - `event_confirmation()` - Confirmation page
  - `EventListView` - Event list/create API
  - `EventDiscoveryView` - Event discovery with filters API
  - `EventDetailView` - Event CRUD API
  - `OrganizerEventManagementView` - Organizer event management API

### Ticket Management
- **`ticket_views.py`** (~145 lines)
  - `TicketIssueView` - Issue tickets API
  - `TicketValidationView` - Validate tickets API
  - `MyTicketsView` - User's tickets API
  - `TicketDetailView` - Ticket detail/cancel API
  - `claim_ticket()` - Claim ticket HTML action
  - `my_events()` - User's events HTML page

### Admin User Management
- **`admin_user_views.py`** (~225 lines)
  - `AdminUserManagementView` - User list with filters
  - `AdminUserDetailView` - User detail/update
  - `AdminUserApprovalView` - Approve/reject users
  - `AdminUserRoleView` - Change user roles
  - `AdminUserStatusView` - Activate/deactivate users
  - `AdminPendingOrganizersView` - Pending organizers list
  - `admin_users_dashboard()` - Users dashboard HTML page

### Admin Event Management
- **`admin_event_views.py`** (~175 lines)
  - `AdminEventModerationView` - Event moderation list
  - `AdminEventDetailView` - Event detail/update
  - `AdminEventApprovalView` - Approve/reject events
  - `AdminEventStatusView` - Change event status
  - `AdminPendingEventsView` - Pending events list
  - `admin_events_dashboard()` - Events dashboard HTML page

### Dashboard & Analytics
- **`dashboard_views.py`** (~140 lines)
  - `AdminDashboardStatsView` - Dashboard statistics API
  - `admin_dashboard_page()` - Dashboard HTML page

### Calendar
- **`calendar_views.py`** (~70 lines)
  - `calendar_page()` - Calendar HTML page
  - `calendar_events_feed()` - FullCalendar JSON feed

### Exports
- **`export_views.py`** (~115 lines)
  - `event_attendees_csv()` - CSV export (session auth)
  - `EventAttendeesCSVListView` - CSV export API (JWT auth)

### Organizer Features
- **`organizer_views.py`** (~125 lines)
  - `organizer_my_events()` - Organizer events dashboard
  - `scan_ticket_image()` - QR code scanning for check-in

## Benefits of This Structure

✅ **Better Organization** - Related views grouped together
✅ **Easier Navigation** - Find views by feature area
✅ **Improved Maintainability** - Smaller files (~25-225 lines each)
✅ **Clear Separation** - Admin, user, and public views separated
✅ **Backward Compatible** - All imports from `campusevents.views` still work
✅ **Team Collaboration** - Multiple developers can work on different files

## Usage

All existing imports continue to work:
```python
from campusevents.views import UserProfileView, EventListView
```

The `__init__.py` re-exports everything, maintaining full backward compatibility.

