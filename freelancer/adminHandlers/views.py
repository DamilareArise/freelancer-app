from django.shortcuts import render
from rest_framework import viewsets
from django.contrib.auth import get_user_model
from freelancer.accounts.permissions import IsAdminUser
from . import serializers as sz

User = get_user_model()

# Create your views here.

class AdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()
    serializer_class = sz.AdminSerializer