from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views as vw 

router = DefaultRouter()
router.register(r'handle-admin', vw.AdminViewSet, basename='admin')