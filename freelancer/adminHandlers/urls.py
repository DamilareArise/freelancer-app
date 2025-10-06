from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views as vw 

router = DefaultRouter()
router.register(r'handle-admin', vw.AdminViewSet, basename='admin')
router.register(r'charges', vw.ChargesViewSet, basename='charges')
router.register(r'faq', vw.FAQViewset, basename='faq')
router.register(r'get-categories', vw.GetCategories, basename='get-categories')
router.register(r'categories', vw.CategoryViewSet, basename='category')
router.register(r"bookings", vw.AllBookings, basename='bookings')
router.register(r'get-reviews', vw.GetReviews, basename='get-reviews')

urlpatterns = [
    path('', include(router.urls)),
    path('create-category/', vw.ServiceCategoryCreateView.as_view(), name='create-category'),
    path('update-category/<int:pk>/', vw.ServiceCategoryCreateView.as_view(), name='update-category'),
    path('handle-doc-aproval/<int:user_id>/', vw.HandleDocumentApproval.as_view(), name='handle-doc-aproval'),
    path('handle-list-status/', vw.HandleListStatus.as_view(), name='handle-list-status'),
    path('user-listings-bookings/<int:id>/', vw.UserWithListingsAndBookings.as_view(), name='user-listings-bookings'),
    path('superad-status/<int:id>/', vw.ChangeSuperAdStatus.as_view(), name='superad-status'), 
    path('extend-superad/<int:id>/', vw.ExtendSuperAd.as_view(), name='extend-superad'),
    path('delete-superad/<int:id>/', vw.DeleteSuperAd.as_view(), name='delete-superad'),
    path('change-superad/<int:id>/', vw.ChangeSuperAdCategory.as_view(), name='change-superad'),
]