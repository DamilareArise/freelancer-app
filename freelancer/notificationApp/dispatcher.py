from accounts.models import User
from .models import NotificationTemplate, Notification
from django.utils import timezone
from .services import SENDER_REGISTRY
from .scheduler import should_send_template



def _resolve_recipients(recipient_list):
    """Return queryset of users based on the recipients field."""
    
    users = User.objects.none()

    # Fetch customers (normal users)
    if "user" in recipient_list:
        customer_qs = User.objects.filter(
            is_active=True,
            user_roles__role__id="CUSTOMER"
        ).exclude(
            user_roles__role__id="SERVICE_PROVIDER"
        )
        users = users.union(customer_qs)

    # Fetch service providers
    if "service_provider" in recipient_list:
        provider_qs = User.objects.filter(
            is_active=True,
            user_roles__role__id="SERVICE_PROVIDER"
        )
        users = users.union(provider_qs)

    return users.distinct()


def dispatch_notifications():
    """Loops through all notification templates and sends notifications."""

    templates = NotificationTemplate.objects.all()

    for template in templates:
        
        if not should_send_template(template):
            continue
        
        recipients = _resolve_recipients(template.recipients)

        for user in recipients:
            for notif_type in template.types:

                sender_class = SENDER_REGISTRY.get(notif_type)
                if not sender_class:
                    continue

                # Create the Notification log row (pending status)
                notification_log = Notification.objects.create(
                    template=template,
                    recipient_user=user,
                    status=Notification.Status.PENDING,
                )

                try:
                    # Initialize and send via the appropriate sender class
                    sender = sender_class(notification_log)
                    sender.send()

                    notification_log.status = Notification.Status.SENT
                    notification_log.sent_at = timezone.now()

                except Exception as e:
                    notification_log.status = Notification.Status.FAILED
                    notification_log.error_message = str(e)

                notification_log.save()
                
        template.last_sent_at = timezone.now()
        template.save()