from django.shortcuts import render
from .models import NotificationTemplate
from .serializers import NotificationTemplateSerializer
from rest_framework import viewsets, filters
from accounts.permissions import IsAdminUser
from accounts.pagination import CustomOffsetPagination

# Create your views here.

class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all().order_by('-created_at')
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAdminUser]
    pagination_class = CustomOffsetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['category', 'header', 'body']
    ordering_fields = ['created_at', 'category']
    ordering = ['-created_at']
    