from rest_framework import viewsets, filters
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
from django.db.models import OuterRef, Exists
from django.utils.timezone import now



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
    serializer_class = AdSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['type']
    
    def get_queryset(self):
        active_super_ads = Ad.objects.filter(
            listing=OuterRef('listing_id'),
            type='super_ads',
            status='active',
            start_date__lte=now(),
            end_date__gte=now()
        )

        queryset = Ad.objects.annotate(
            has_super_ads=Exists(active_super_ads)
        )
        
        return queryset.filter(listing__created_by=self.request.user)

class AdImpressionViewSet(viewsets.ModelViewSet):
    queryset = Impression.objects.all()
    serializer_class = ImpressionSerializer
    permission_classes = [IsAuthenticated]
    