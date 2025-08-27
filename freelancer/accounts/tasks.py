from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from celery import shared_task
import logging 

logger = logging.getLogger(__name__)

@shared_task
def send_email(context, file=None):
    try:
        html_message = render_to_string(file, context=context)
        plain_message = strip_tags(html_message)

        d_email = EmailMultiAlternatives(
            subject=context['subject'],
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[context['email']],
        )

        d_email.attach_alternative(html_message, 'text/html')
        d_email.send(fail_silently=False)

    except Exception as e:
        logger.error(f"Error sending email: {e}")