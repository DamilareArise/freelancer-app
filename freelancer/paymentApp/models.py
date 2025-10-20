from django.db import models
from listing.models import Listing
from adminHandlers.models import CategoryPricing
from adsApp.models import SuperAdsCategory

# Create your models here.

class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled')
    )
    
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='payments')
    price = models.ForeignKey(CategoryPricing, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=255, unique=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    super_ad = models.ForeignKey(SuperAdsCategory, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    super_ad_month = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)