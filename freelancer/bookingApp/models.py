from django.db import models
from accounts.models import User
from listing.models import Listing

# Create your models here.

class Availability(models.Model):
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='availability')
    day = models.CharField(max_length=10, choices=DAY_CHOICES, null=True)
    slots = models.JSONField(null=True)
    

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('canceled', 'Canceled'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='booking')
    date_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='booking_requester')
    unit_count = models.PositiveIntegerField(default=1)
    contact_name = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=15)
    canceled_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='booking_canceled_by', null=True)
    canceled_at = models.DateTimeField(null=True)
    cancel_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
class Reviews(models.Model):
    IMPRESSIONS_CHOICES = (
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative')
    )
    
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviewer')
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank=True, null=True)
    impression = models.CharField(max_length=10, choices=IMPRESSIONS_CHOICES, default='positive')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('booking', 'reviewer')