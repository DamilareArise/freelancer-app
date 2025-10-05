from rest_framework import viewsets
from .models import SuperAdsCategory, AppLocation, SuperAdsCategoryLocation, Ad, Impression
from .serializers import (
    SuperAdsCategorySerializer, 
    AppLocationSerializer, 
    SuperAdsCategoryLocationSerializer, 
    AdSerializer,
    ImpressionSerializer
)
from accounts.permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticated


class SuperAdsCategoryViewSet(viewsets.ModelViewSet):
    queryset = SuperAdsCategory.objects.all()
    serializer_class = SuperAdsCategorySerializer
    permission_classes = [IsAdminUser]
    
class AppLocationViewSet(viewsets.ModelViewSet):
    queryset = AppLocation.objects.all()
    serializer_class = AppLocationSerializer
    permission_classes = [IsAdminUser]

class SuperAdsCategoryLocationViewSet(viewsets.ModelViewSet):
    queryset = SuperAdsCategoryLocation.objects.all()
    serializer_class = SuperAdsCategoryLocationSerializer   
    permission_classes = [IsAuthenticated]

class AdViewSet(viewsets.ModelViewSet):
    queryset = Ad.objects.all()
    serializer_class = AdSerializer
    permission_classes = [IsAuthenticated]

class AdImpressionViewSet(viewsets.ModelViewSet):
    queryset = Impression.objects.all()
    serializer_class = ImpressionSerializer
    permission_classes = [IsAuthenticated]
    