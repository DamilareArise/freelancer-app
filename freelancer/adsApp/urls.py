from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SuperAdsCategoryViewSet, AppLocationViewSet, SuperAdsCategoryLocationViewSet, AdViewSet, AdImpressionViewSet

router = DefaultRouter()

router.register(r'super-ads-categories', SuperAdsCategoryViewSet, basename='super-ads-categories')
router.register(r'app-locations', AppLocationViewSet, basename='app-locations')
router.register(r'super-ads-category-locations', SuperAdsCategoryLocationViewSet, basename='super-ads-category-locations')
router.register(r'ads-subscription', AdViewSet, basename='ads-subscription' )
router.register(r'ad-impressions', AdImpressionViewSet, basename='ad-impressions')
    
urlpatterns = [
    path('', include(router.urls)),
]
