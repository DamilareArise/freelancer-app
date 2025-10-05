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
    permission_classes = [IsAdminUser]
    queryset = ServiceCategory.objects.order_by('-created_at')
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
        """Handle delete exceptions"""
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response({"message": "Category deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except RestrictedError as e:
            return Response(
                {"error": "This category has related listings and cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST
            ) 
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
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
    queryset = ServiceCategory.objects.order_by('-created_at')
    
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
                    'listing': listing,
                    'rejection_reasons': rejection_reasons,
                    'user': listing.created_by.id
                }
                send_email.delay(context, file='rejected.html')
                

        else:
            listings.update(status="approved")
            for listing in listings:
                context = {
                    'subject': 'Listing Approval Notification',
                    'listing': listing,
                    'user': listing.created_by.id
                }
                send_email.delay(context, file='approved.html')
                

        return Response({"message": "Listings updated successfully."}, status=status.HTTP_200_OK)