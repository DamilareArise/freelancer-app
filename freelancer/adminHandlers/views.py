from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from django.contrib.auth import get_user_model
from accounts.permissions import IsAdminUser
from . import serializers as sz
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import FAQ, Charges, ServiceCategory
from django.db.models.deletion import RestrictedError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from accounts.tasks import send_email
from listing.models import Listing
from rest_framework.generics import RetrieveAPIView
from bookingApp.models import Booking
from bookingApp.serializers import BookingSerializer
from django.db.models import Q
from accounts.pagination import CustomOffsetPagination
from adsApp.models import Ad
from datetime import timedelta
from adsApp.models import SuperAdsCategory
from bookingApp.models import Reviews
from notificationApp.models import Notification


User = get_user_model()

# Create your views here.


class AdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()
    serializer_class = sz.AdminSerializer
    
class FAQViewset(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = FAQ.objects.all().order_by('rank')
    serializer_class = sz.FAQSerializer
    
class ChargesViewSet(viewsets.ModelViewSet):
    queryset = Charges.objects.all()
    serializer_class = sz.ChargesSerializer
    permission_classes = [IsAdminUser]
    
class CategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ServiceCategory.objects.all()
    serializer_class = sz.ServiceCategoryUnifiedSerializer
    
    
    # def get_serializer_class(self):
    #     if self.action == 'retrieve' or self.action == 'list':
    #         return sz.ServiceCategoryUnifiedSerializer
    #     return sz.ServiceCategorySerializer
    
    def perform_create(self, serializer):
        """Set the created_by field automatically"""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Set the updated_by field automatically"""
        serializer.save(updated_by=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Category deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        
class ServiceCategoryCreateView(APIView):
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        serializer = sz.ServiceCategoryUnifiedSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return Response(sz.ServiceCategoryUnifiedSerializer(category).data, status=status.HTTP_201_CREATED)
    
    def put(self, request, pk):
        try:
            category_instance = ServiceCategory.objects.get(pk=pk)
        except ServiceCategory.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = sz.ServiceCategoryUnifiedSerializer(category_instance, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return Response(sz.ServiceCategoryUnifiedSerializer(category).data, status=status.HTTP_200_OK)
        
# Api for the mobile phase
class GetCategories(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = sz.ServiceCategoryUnifiedSerializer
    queryset = ServiceCategory.objects.all()
    
class HandleDocumentApproval(APIView):
    permission_classes = [IsAdminUser]
    
    def patch(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        action = request.data.get('action')
        message = request.data.get('message')
        
        if action not in ['approve', 'reject']:
            return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)
        
        if action == "approve":
            user.document_status = 'verified'
            template = 'document_approved.html'
            subject = 'Document Verification Approval Notification'
        else:
            user.document_status = 'rejected'
            template = 'document_rejected.html'
            subject = 'Document Verification Rejection Notification'
        
        user.save()

        
        context = {
            'subject': subject,
            'user': user.id,         
            'role': "Service Provider",
            'message': message
        }

        send_email.delay(context, template)
        
        # in-app Notification 
        Notification.objects.create(
            recipient_user=user,
            title="Document Verification Update",
            message=f"Your document verification has been {action}ed.",
            data={"status": user.document_status},
            status=Notification.Status.SENT
        )

        return Response({"message": "Document status updated successfully."}, status=status.HTTP_200_OK)
    
class HandleListStatus(APIView):
    permission_classes = [IsAdminUser]
    def patch(self, request, *args, **kwargs):
        listing_ids = request.data.get("listing_ids")
        action = request.data.get('action')
        if not listing_ids:
            return Response({"error": "Listing IDs are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if action not in ['reject', 'approve']:
            return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)
        
        listings = Listing.objects.filter(id__in=listing_ids)
        if not listings.exists():
            return Response({"error": "No valid listings found."}, status=status.HTTP_404_NOT_FOUND)

        if action == "reject":
            rejection_reasons = request.data.get("rejection_reasons")
            if not rejection_reasons:
                return Response({"error": "Rejection reasons are required."}, status=status.HTTP_400_BAD_REQUEST)

            listings.update(status="rejected", rejection_reasons=rejection_reasons)
            for listing in listings:
                context = {
                    'subject': 'Listing Rejection Notification',
                    'listing': listing.id,
                    'rejection_reasons': rejection_reasons,
                    'user': listing.created_by.id
                }
                send_email.delay(context, file='rejected.html')
                

        else:
            listings.update(status="approved")
            for listing in listings:
                context = {
                    'subject': 'Listing Approval Notification',
                    'listing': listing.id,
                    'user': listing.created_by.id
                }
                send_email.delay(context, file='approved.html')
                

        return Response({"message": "Listings updated successfully."}, status=status.HTTP_200_OK)
    
class UserWithListingsAndBookings(RetrieveAPIView):
    permission_classes = [IsAdminUser]
    queryset = User.objects.prefetch_related('listings', 'user_roles__role', 'booking_requester__listing').all()
    serializer_class = sz.UserWithListingsSerializer
    lookup_field = 'id'
    
class AllBookings(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = Booking.objects.all().order_by('-created_at')
    serializer_class = BookingSerializer
    pagination_class = CustomOffsetPagination
    
    def get_queryset(self):
        
        params = self.request.query_params
        status = params.get('status')
        search = params.get('search')
        queryset = self.queryset
        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(
                Q(listing__property__header__icontains=search) | 
                Q(requester__first_name__icontains=search) |
                Q(requester__last_name__icontains=search) |
                Q(listing__location__city__icontains=search) |
                Q(listing__location__country__icontains=search) |
                Q(listing__location__county__icontains=search) 
            )
        return queryset

class ChangeSuperAdStatus(APIView):
    permission_classes = [IsAdminUser]
    
    def patch(self, request, id):
        action = request.data.get('action')
        if action not in ['paused', 'active']:
            return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)
        super_ad = get_object_or_404(Ad, id=id, type='super_ads')
        super_ad.status = action
        super_ad.save()
        return Response({"message": f"Super Ad status changed to {action}."}, status=status.HTTP_200_OK) 
    
class DeleteSuperAd(APIView):
    permission_classes = [IsAdminUser]
    
    def delete(self, request, id):
        super_ad = get_object_or_404(Ad, id=id, type='super_ads')
        super_ad.delete()
        return Response({"message": "Super Ad deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
    
class ExtendSuperAd(APIView):
    permission_classes = [IsAdminUser]
    
    def patch(self, request, id):
        super_ad = get_object_or_404(Ad, id=id, type='super_ads')
        days= request.data.get('days')
        if not days:
            return Response({"error": "Days are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not isinstance(days, int) or days <= 0:
            return Response({"error": "Days must be a positive integer."}, status=status.HTTP_400_BAD_REQUEST)
        
        super_ad.end_date += timedelta(days=days)
        super_ad.save()
        return Response({"message": f"Super Ad extended by {days} day(s) successfully."}, status=status.HTTP_200_OK)
    
class ChangeSuperAdCategory(APIView):
    permission_classes = [IsAdminUser]
    
    def patch(self, request, id):
        super_ad = get_object_or_404(Ad, id=id, type='super_ads')
        new_category_id = request.data.get('category_id')
        if not new_category_id:
            return Response({"error": "New category ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        new_category = get_object_or_404(SuperAdsCategory, id=new_category_id)
        super_ad.super_ads_category = new_category
        super_ad.save()
        
        return Response({"message": "Super Ad category changed successfully."}, status=status.HTTP_200_OK)
    
class GetReviews(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminUser]
    pagination_class = CustomOffsetPagination
    serializer_class = sz.AdminReviewSerializer
    queryset = Reviews.objects.all().order_by('-created_at')
    

