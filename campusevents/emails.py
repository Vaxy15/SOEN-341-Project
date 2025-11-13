import io, qrcode, hashlib
from email.utils import make_msgid
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.translation import gettext as _
from .email_tokens import make_email_token

def _qr_png(data: str) -> bytes:
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def make_send_key(to_email: str, ticket_id: str, template: str) -> str:
    raw = f"{to_email}|{ticket_id}|{template}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def build_confirmation_message(
    *, to_email: str, user_name: str,
    event_title: str, event_dt, location: str,
    ticket_id: str, seat: str|None, organizer: str, support_email: str,
) -> EmailMultiAlternatives:

    token = make_email_token(f"{ticket_id}:{to_email}")
    view_url = f"{settings.APP_BASE_URL}/tickets/view/?token={token}"

    ctx = {
        "user_name": user_name,
        "event_title": event_title,
        "event_dt": event_dt,             # aware dt in America/Toronto display
        "location": location,
        "ticket_id": ticket_id,
        "seat": seat,
        "organizer": organizer,
        "support_email": support_email,
        "view_url": view_url,
    }

    subject = _("Your ticket for %(event)s") % {"event": event_title}
    text_body = render_to_string("campusevents/email/claim_confirmation.txt", ctx)
    html_body = render_to_string("campusevents/email/claim_confirmation.html", ctx)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
        headers={
            "X-Transactional": "true",
            "Message-ID": make_msgid("campusevents"),
        },
    )
    msg.attach_alternative(html_body, "text/html")

    qr_bytes = _qr_png(view_url)
    msg.attach(filename="ticket_qr.png", content=qr_bytes, mimetype="image/png")

    return msg
