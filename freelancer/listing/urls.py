from . import views as vw
from rest_framework.routers import DefaultRouter
from django.urls import path, include


router = DefaultRouter()
router.register(r'listings', vw.ListingViewSet)
router.register(r'resources', vw.ResourceViewSet)
router.register(r'user-listings', vw.UserListings, basename='user-listings')
router.register(r'favorites', vw.FavoriteViewset, basename='favorites')
router.register(r'favorited-listings', vw.GetFavoritedListings, basename='favorited')

urlpatterns = [
    path('user/', include(router.urls)),
    path('summary/', vw.Summary.as_view(), name='summary'), 
    path('listing-availability/<int:listing_id>/', vw.UpdateAvailability.as_view(),name='listing-availability'),
]