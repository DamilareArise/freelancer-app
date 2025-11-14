from django.db import models
from accounts.models import User
from listing.models import Listing

# Create your models here.
class Conversation(models.Model):
    
    status_choices = (
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('blocked', 'Blocked'),
    )
    type_choices = (
        ('regular', 'Regular'),
        ('support', 'Support')
    )
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_conversations')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_conversations', null=True, blank=True)
    status = models.CharField(max_length=20, choices=status_choices, default='active')
    type = models.CharField(max_length=20, choices=type_choices, default='regular')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class Chat(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='chats')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_chats')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    resource = models.FileField(upload_to='chat_resources/', null=True, blank=True)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='chats', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 


class SupportType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class SupportTicket(models.Model):
    status_choices = (
        ('open', 'Open'),
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
        ('escalated', 'Escalated'),
    )
    
    complainant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_tickets')
    support_type = models.ForeignKey(SupportType, on_delete=models.CASCADE, related_name='tickets')
    status = models.CharField(max_length=20, choices=status_choices, default='pending')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='support_tickets', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    