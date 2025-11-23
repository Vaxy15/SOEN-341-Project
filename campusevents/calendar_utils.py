# campusevents/calendar_utils.py

import urllib.parse
from icalendar import Calendar, Event as ICalEvent
from django.utils import timezone
from django.http import HttpResponse
from django.urls import reverse


def generate_ics_file(event, request):
    """
    Generate an .ics file for an event.
    
    Args:
        event: Event model instance
        request: Django request object (for building absolute URL)
    
    Returns:
        HttpResponse with .ics file
    """
    # Create calendar
    cal = Calendar()
    cal.add('prodid', '-//Campus Events//Campus Events Calendar//EN')
    cal.add('version', '2.0')

    # Create event
    ical_event = ICalEvent()

    # Generate unique UID based on event ID
    uid = f"campusevent-{event.id}-{event.updated_at.timestamp()}@{request.get_host()}"
    ical_event.add('uid', uid)

    # Add event details
    ical_event.add('summary', event.title)
    ical_event.add('description', event.description)
    ical_event.add('location', event.location)

    # Start and end times (convert to UTC if needed)
    ical_event.add('dtstart', event.start_at)
    ical_event.add('dtend', event.end_at)

    # Timestamp
    ical_event.add('dtstamp', timezone.now())

    # URL back to event page
    event_url = request.build_absolute_uri(
        reverse('event_detail', args=[event.id])
    )
    ical_event.add('url', event_url)

    # Add status (for ongoing events)
    if event.status == 'approved':
        ical_event.add('status', 'CONFIRMED')
    else:
        ical_event.add('status', 'TENTATIVE')

    cal.add_component(ical_event)

    # Generate response
    response = HttpResponse(cal.to_ical(), content_type='text/calendar; charset=utf-8')

    # Set filename
    filename = f"event_{event.id}_{event.title.replace(' ', '_')}.ics"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Prevent caching
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response


def generate_google_calendar_link(event, request):
    """
    Generate a Google Calendar link for an event.
    
    Args:
        event: Event model instance
        request: Django request object (for building absolute URL)
    
    Returns:
        str: Google Calendar URL
    """
    # Build base URL
    base_url = 'https://calendar.google.com/calendar/render'

    # Build event URL
    event_url = request.build_absolute_uri(
        reverse('event_detail', args=[event.id])
    )

    # Format dates for Google Calendar (YYYYMMDDTHHmmssZ)
    start_date = event.start_at.strftime('%Y%m%dT%H%M%S')
    end_date = event.end_at.strftime('%Y%m%dT%H%M%S')

    # URL encode parameters (Google Calendar accepts multiple sprop parameters)
    params = [
        ('action', 'TEMPLATE'),
        ('text', event.title),
        ('dates', f'{start_date}/{end_date}'),
        ('details', event.description),
        ('location', event.location),
        ('ctz', 'America/Toronto'),  # Timezone
        ('sprop', 'name:Campus Events'),
        ('sprop', f'website:{event_url}')
    ]

    # Build query string with proper URL encoding
    query_string = '&'.join([f'{k}={urllib.parse.quote(str(v))}' for k, v in params])
    url = f'{base_url}?{query_string}'

    return url

