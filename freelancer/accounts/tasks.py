from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from celery import shared_task
import logging
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from accounts.models import User
from django.utils.timezone import now
from adsApp.models import Ad

User = get_user_model()

logger = logging.getLogger(__name__)

@shared_task
def send_email(context, file=None):
    user_id = context.get('user')
    email = context.get('email')
    context['user'] = User.objects.filter(id=user_id).first() if user_id else None
    
    if context.get('booking'):
        from bookingApp.models import Booking
        context['booking'] = Booking.objects.filter(id=context['booking']).first()
    
    if context.get('listing'):
        from listing.models import Listing
        context['listing'] = Listing.objects.filter(id=context['listing']).first()
    
    if context.get('payment'):
        from paymentApp.models import Payment
        context['payment'] = Payment.objects.filter(id=context['payment']).first()
    
    if context.get('ad'):
        from adsApp.models import Ad
        context['ad'] = Ad.objects.filter(id=context['ad']).first()
    
    try:
        html_message = render_to_string(file, context=context)
        plain_message = strip_tags(html_message)

        d_email = EmailMultiAlternatives(
            subject=context['subject'],
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email if email else context['user'].email],
        )

        d_email.attach_alternative(html_message, 'text/html')
        d_email.send(fail_silently=False)

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        

@shared_task
def delete_inactive_users():
    cutoff = timezone.now() - timedelta(days=23)
    users = User.objects.filter(status="inactive", deactivation_requested_at__lte=cutoff)

    count = users.count()
    for user in users:
        user.is_active = False 
        user.save()
    
    return f"Deleted {count} users"



@shared_task
def expire_ads_if_needed():
    Ad.objects.filter(
        end_date__lt=now(),
        status='active'
    ).update(status='expired')
