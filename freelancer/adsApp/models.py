from django.db import models
from listing.models import Listing
from accounts.models import User

# Create your models here.
class SuperAdsCategory(models.Model):
    TIER_CHOICES = (
        (1, 'Tier 1'),
        (2, 'Tier 2'), 
        (3, 'Tier 3')
    )
    
    title = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tier = models.IntegerField(choices=TIER_CHOICES, default=1)
    features = models.JSONField(default=list)

    def __str__(self):
        return f"{self.title} - Tier {self.tier}"


class AppLocation(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class SuperAdsCategoryLocation(models.Model):
    super_ads_category = models.ForeignKey(SuperAdsCategory, on_delete=models.CASCADE, related_name='locations')
    app_location = models.ForeignKey(AppLocation, on_delete=models.CASCADE, related_name='super_ads_categories')

    def __str__(self):
        return f"{self.super_ads_category} - {self.app_location}"


class Ad(models.Model):
    TYPE_CHOICES = (
        ('super_ads', 'Super Ads'),
        ('regular_ads', 'Regular Ads'),
    )
    
    STATUS_CHOICES = (
        ('paused', 'Paused'),
        ('active', 'Active'),
        ('expired', 'Expired')
    )
    
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='ads')
    super_ads_category = models.ForeignKey(SuperAdsCategory, on_delete=models.CASCADE, related_name='ads', null=True, blank=True)
    type = models.CharField(max_length=255, choices=TYPE_CHOICES)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class Impression(models.Model):
    TYPE_CHOICE = [
        ('impression', 'Impression'),
        ('click', 'Click')
    ]
    
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='impressions')
    type = models.CharField(max_length=20, choices=TYPE_CHOICE, default='impression')
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='impressions', null=True, blank=True)
    
    def __str__(self):
        return f"Impression for {self.ad} at {self.timestamp}"