from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Ticket
from .tasks import send_ticket_confirmation_email

@receiver(post_save, sender=Ticket, dispatch_uid="campusevents.ticket_post_save_email_v1")
def trigger_ticket_email(sender, instance, created, **kwargs):
    if created:
        send_ticket_confirmation_email.delay(instance.id)
