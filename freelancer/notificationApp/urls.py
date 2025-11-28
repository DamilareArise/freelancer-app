from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationTemplateViewSet

router = DefaultRouter()
router.register(r'templates', NotificationTemplateViewSet, basename='templates')

urlpatterns = [
    path('', include(router.urls)),
]