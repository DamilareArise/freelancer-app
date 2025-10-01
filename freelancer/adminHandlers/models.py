from django.db import models
from accounts.models import User


class PropertyCategory(models.Model):
    name_en=models.CharField(max_length=255, unique=False)
    name_hr=models.CharField(max_length=255, null=True, blank=True)
    icon = models.CharField(max_length=50, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='created_categories', null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='updated_categories', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name_en}"


class CategoryPricing(models.Model):
    category = models.ForeignKey(PropertyCategory, on_delete=models.CASCADE, related_name='category_pricing')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.PositiveIntegerField(null=True, blank=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='created_pricing', null=True, blank=True)

    def __str__(self):
        return f"{self.category} - {self.price}"


class CategoryFeaturesField(models.Model):
    TYPE_CHOICES = (
        ('text', 'Text'),
        ('number', 'Number'),
        ('select', 'Select'),
        ('checkbox', 'Checkbox'),
        ('radio', 'Radio'),
    )

    category = models.ForeignKey(PropertyCategory, on_delete=models.CASCADE, related_name='category_features')
    label_en=models.CharField(max_length=255)
    label_hr=models.CharField(max_length=255, null=True, blank=True)
    unit=models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=255, choices=TYPE_CHOICES)
    required = models.BooleanField(default=False)
    options = models.JSONField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='created_features', null=True, blank=True)

    def __str__(self):
        return f"{self.category.name_en} - {self.label_en}"


class SubCategory(models.Model):
    category = models.ForeignKey(PropertyCategory, on_delete=models.CASCADE, related_name='subcategories')
    name_en=models.CharField(max_length=255)
    name_hr=models.CharField(max_length=255, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='created_subcategories', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name_en


class FAQ(models.Model):
    question_en=models.CharField(max_length=255)
    question_hr=models.CharField(max_length=255, null=True, blank=True)
    answer_en=models.TextField()
    answer_hr=models.TextField(null=True, blank=True)
    rank = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='created_faqs', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Charges(models.Model):
    charge_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    charge_fixed = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    for_key = models.CharField(max_length=50, unique=True, blank=True, null=True)
    for_label = models.CharField(max_length=100, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)