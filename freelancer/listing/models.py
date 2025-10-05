from django.db import models
from accounts.models import User
from adminHandlers.models import ServiceCategory, SubCategory, CategoryFeaturesField
from django.db.models.signals import post_save
from django.dispatch import receiver
import tinify
from django.conf import settings



tinify.key = settings.TINIFY_API_KEY


# Create your models here.
class Contact(models.Model):
    fullname = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    phone2 = models.CharField(max_length=20, blank=True, null=True)
    website = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return self.fullname

class Location(models.Model):
    country = models.CharField(max_length=100)
    county = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    street_name = models.CharField(max_length=255)
    street_number = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.street_name}, {self.city}, {self.country}"
    
class Service(models.Model):
    header = models.CharField(max_length=255)
    description_en = models.TextField()
    description_hr = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.header
    

class Listing(models.Model):    
    USER_TYPE_CHOICES = (
        ('private', 'Private'),
        ('agency/business', 'Agency/Business')
    )
        
    LISTING_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired')
    )
    
    
    category = models.ForeignKey(ServiceCategory, on_delete=models.RESTRICT, related_name='listings')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True)
    user_type = models.CharField(max_length=50, choices=USER_TYPE_CHOICES, default='private')
    location = models.OneToOneField(Location, on_delete=models.CASCADE)
    contact = models.OneToOneField(Contact, on_delete=models.CASCADE)
    service = models.OneToOneField(Service, on_delete=models.CASCADE)    
    price = models.DecimalField(max_digits=12, decimal_places=2)
    price_unit = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(choices=LISTING_STATUS, default='pending', max_length=50)
    available = models.BooleanField(default=True)
    rejection_reasons = models.JSONField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.service.header if self.service else 'No Title'} - {self.price}"
    
class ListingFeatures(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='features')
    feature_field = models.ForeignKey(CategoryFeaturesField, on_delete=models.RESTRICT, null=True, blank=True)
    value = models.JSONField()
    
    def __str__(self):
        return f"{self.listing.service.header if self.listing.service else 'No Title'} - {self.feature_field.label} - {self.value}"

class Resource(models.Model):
    RESOURCE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    
    
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='resources')
    resource = models.FileField(upload_to='listingResources/', max_length=100)
    type = models.CharField(max_length=50, choices=RESOURCE_TYPE_CHOICES, default='image')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_cover = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name
    
@receiver(post_save, sender=Resource)
def compress_resource_image(sender, instance, **kwargs):
    if instance.type == 'image' and instance.resource:
        try:
            file_path = instance.resource.path
            source = tinify.from_file(file_path)
            source.to_file(file_path)
            print(f"Compressed: {file_path}")
        except Exception as e:
            print(f"Compression error: {e}")
            
            

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'listing')  # Prevent duplicate favorites