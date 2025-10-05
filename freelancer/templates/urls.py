from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views as vw

router = DefaultRouter()
router.register(r'available', vw.AvailableViewSet, basename='available')
router.register(r'bookings', vw.BookingViewSet, basename='bookings')
router.register(r"booking-management", vw.BookingManagementViewSet, basename='booking-management')
router.register(r"reviews",vw.ReviewViewSet, basename='reviews')

urlpatterns = [
    path('', include(router.urls)),
    path('user-availability/<int:listing_id>/', vw.GetUserAvailability.as_view()),
    path('get-reviews/<int:listing_id>/', vw.GetReviews.as_view(), name='get-reviews'),
]
