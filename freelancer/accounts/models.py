from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.translation import gettext_lazy as _
import pyotp
from django_countries.fields import CountryField


class UserManager(BaseUserManager):
    def email_validator(self, email):
        try:
            validate_email(email)
        except ValidationError:
            raise ValueError(_("Please enter a valid email address"))
        
    def create_user(self, email, first_name, last_name, password, **extra_fields):
        if email:
            email = self.normalize_email(email)
            self.email_validator(email)
        else:
            raise ValueError(_("An email address is required"))

        if not first_name:
            raise ValueError(_("First name is required"))
        
        if not last_name:
            raise ValueError(_("Last name is required"))
        
        user = self.model(email=email, first_name=first_name, last_name= last_name, **extra_fields)
        user.set_password(password)
        user.save(using = self._db)
        return user
    

    
class User(AbstractBaseUser, PermissionsMixin):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('pending', 'Pending'),
    )
    
    DOC_TYPE = [
        ('passport', 'Passport'),
        ('id_card', 'ID Card'),
        ('driver_license', 'Driver License'),
        ('residence_permit', 'Residence Permit'),
        ('other', 'Other'),
    ]
    
    DOC_VERIFICATION_STATUS = [
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('submitted', 'Submitted'),
        ('pending', 'Pending'),
    ]
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(unique=True, max_length=15)
    address = models.OneToOneField('Address', on_delete=models.SET_NULL, null=True, blank=True)
    website = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='active')
    passport = models.ImageField(upload_to='passport/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    otp_secret = models.CharField(max_length=32, blank=True, null=True)
    vat = models.CharField(max_length=30, null=True, blank=True)
    oib = models.CharField(max_length=30, null=True, blank=True)
    document_type = models.CharField(max_length=30, choices=DOC_TYPE, null=True, blank=True)
    document = models.FileField(upload_to='user_document/', null=True, blank=True)
    business_reg = models.FileField(upload_to='business_reg/', null=True, blank=True)
    auth_letter = models.FileField(upload_to='auth_letter/', null=True, blank=True)
    document_status = models.CharField(max_length=20, choices=DOC_VERIFICATION_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    selfie = models.ImageField(upload_to='selfie/', null=True, blank=True) 
    deactivation_requested_at = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone']
    
    def __str__(self):
        return self.email
    
    @property
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def generate_otp(self):
        if not self.otp_secret:
            self.otp_secret = pyotp.random_base32()
            self.save()
        totp = pyotp.TOTP(self.otp_secret, digits=4, interval=600)
        otp = totp.now()
        return otp
    
    def verify_otp(self, otp):
        totp = pyotp.TOTP(self.otp_secret, digits=4, interval=600)
        return totp.verify(otp)
    
    def has_role(self, *role_ids) -> bool:
        """
        Check if the user has any of the given role IDs.
        Example: user.has_role("SUPER", "FINANCE")
        """
        return self.user_roles.filter(role__id__in=role_ids).exists()
    
    def is_admin_role(self) -> bool:
        """Check if user has any role marked as admin"""
        return self.user_roles.filter(role__is_admin=True).exists()

class Address(models.Model):
    country = CountryField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True, null=True)
    street = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.street}, {self.city}, {self.country.name}"


class Role(models.Model):
    id = models.CharField(max_length=30, primary_key=True)
    label = models.CharField(max_length=100, unique=True)
    is_admin = models.BooleanField(default=False)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.label


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_users', default="CUSTOMER")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name} - {self.role.label}"