# 📅 Event Calendar Integration Feature

## Overview
This feature allows students to save events to their personal calendar by downloading .ics files or adding events directly to Google Calendar.

## Implementation Details

### File Structure
- `campusevents/calendar_utils.py` - Calendar utility functions
- `campusevents/views.py` - Calendar API views
- `campusevents/urls.py` - Calendar URL patterns

### API Endpoints

#### 1. Download .ics File
**Endpoint**: `GET /api/events/<pk>/calendar/ics/`

**Description**: Download an .ics file for a specific event that can be imported into any calendar application.

**Authentication**: Required (JWT)

**Response**: 
- HTTP 200 with .ics file
- Content-Type: text/calendar
- Headers set to prevent caching

**Usage Example**:
```javascript
// Frontend implementation
fetch(`/api/events/${eventId}/calendar/ics/`, {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
.then(response => response.blob())
.then(blob => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `event_${eventId}.ics`;
  a.click();
  window.URL.revokeObjectURL(url);
});
```

#### 2. Get Google Calendar Link
**Endpoint**: `GET /api/events/<pk>/calendar/google/`

**Description**: Get a link to add the event to Google Calendar.

**Authentication**: Required (JWT)

**Response**:
```json
{
  "google_calendar_link": "https://calendar.google.com/calendar/render?...",
  "message": "Open this link in a new tab to add the event to your Google Calendar"
}
```

**Usage Example**:
```javascript
// Frontend implementation
fetch(`/api/events/${eventId}/calendar/google/`, {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
.then(response => response.json())
.then(data => {
  window.open(data.google_calendar_link, '_blank');
});
```

## .ics File Contents

The generated .ics file includes:
- **UID**: Unique identifier based on event ID and timestamp
- **Summary**: Event title
- **Description**: Event description
- **Location**: Event location
- **dtstart**: Start date/time
- **dtend**: End date/time
- **dtstamp**: Current timestamp
- **URL**: Link back to event page
- **Status**: CONFIRMED or TENTATIVE

## Google Calendar Integration

The Google Calendar link includes:
- Event title
- Start and end dates/times
- Event description
- Location
- Timezone (America/Toronto)
- Source properties (name and website)

## Features

✅ **Download .ics File** - Import into any calendar app (Google Calendar, Outlook, Apple Calendar)  
✅ **Google Calendar Direct Link** - One-click add to Google Calendar  
✅ **Unique Event Identifiers** - Each event has a unique UID  
✅ **Timezone Support** - Proper timezone handling  
✅ **Cache Prevention** - Headers set to prevent caching issues  
✅ **Event Updates** - UID includes timestamp for tracking changes  
✅ **Mobile & Desktop Compatible** - Works on all devices  

## Testing

### Test with Google Calendar
1. Login to your application
2. Navigate to an event detail page
3. Click "Add to Google Calendar" button
4. Click the returned link (opens in new tab)
5. Verify event details are pre-filled
6. Click "Add to calendar" in Google Calendar

### Test with .ics File
1. Login to your application
2. Navigate to an event detail page
3. Click "Download .ics file" button
4. Import the file into Google Calendar, Outlook, or Apple Calendar
5. Verify event details are correct

### Test with Outlook
1. Download .ics file
2. Open Outlook
3. Go to File > Open & Export > Open Calendar
4. Select the downloaded .ics file
5. Verify the event appears in your calendar

### Test Event Updates
1. Create/select an event
2. Download .ics file (note the timestamp in UID)
3. Update the event (change time/location)
4. Download .ics file again
5. Verify new timestamp in UID
6. Both files should work correctly in calendar apps

## Accessibility

- **Clear Labels**: "Download .ics file" and "Add to Google Calendar" buttons
- **Success Messages**: User receives confirmation when file is downloaded
- **Screen Reader Support**: Proper ARIA labels can be added in frontend
- **Keyboard Navigation**: Full keyboard support for download actions

## Error Handling

- **Event Not Found**: Returns 404 with error message
- **Authentication Required**: Returns 401 if user is not authenticated
- **Invalid Event Data**: Server-side validation ensures proper formatting

## Future Enhancements

- [ ] Recurring events support
- [ ] Custom calendar options
- [ ] Bulk calendar export
- [ ] Calendar synchronization
- [ ] Event reminder configuration

