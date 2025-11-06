# campusevents/views/utils.py
"""
Shared utilities and helper functions for views.
"""

from datetime import datetime
import json

import numpy as np
import cv2

from django.db.models import Q
from django.utils import timezone

from rest_framework.pagination import PageNumberPagination

from ..models import Event


class EventPagination(PageNumberPagination):
    """Custom pagination for events."""
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def build_event_discovery_qs(request):
    """Build filtered queryset for event discovery."""
    qs = (
        Event.objects
        .filter(status=Event.APPROVED, end_at__gte=timezone.now())
        .select_related("org")
        .order_by("start_at")
    )

    get_param = getattr(request, "query_params", request.GET)
    category = get_param.get("category")
    organization = get_param.get("organization")
    date_from = get_param.get("date_from")
    date_to = get_param.get("date_to")
    search = get_param.get("search")

    def parse_date(dt):
        try:
            return datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return None

    if category:
        qs = qs.filter(category__icontains=category)
    if organization:
        qs = qs.filter(org__name__icontains=organization)
    if date_from and (df := parse_date(date_from)):
        qs = qs.filter(start_at__gte=df)
    if date_to and (dtv := parse_date(date_to)):
        qs = qs.filter(start_at__lte=dtv)
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(location__icontains=search)
        )
    return qs


def decode_qr_from_uploaded(django_file):
    """
    Try to decode a QR code from an uploaded image.
    Returns the decoded string (payload) or None.
    """
    data = django_file.read()
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    detector = cv2.QRCodeDetector()
    text, points, _ = detector.detectAndDecode(img)
    return text.strip() if text else None

