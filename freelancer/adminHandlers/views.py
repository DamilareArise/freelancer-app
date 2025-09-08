from django.shortcuts import render
from rest_framework import viewsets
from django.contrib.auth import get_user_model
from accounts.permissions import IsAdminUser
from . import serializers as sz
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import FAQ, Charges, PropertyCategory
from django.db.models.deletion import RestrictedError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView


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
    queryset = PropertyCategory.objects.order_by('-created_at')
    serializer_class = sz.PropertyCategoryUnifiedSerializer
    
    
    # def get_serializer_class(self):
    #     if self.action == 'retrieve' or self.action == 'list':
    #         return sz.PropertyCategoryUnifiedSerializer
    #     return sz.PropertyCategorySerializer
    
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
        
class PropertyCategoryCreateView(APIView):
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        serializer = sz.PropertyCategoryUnifiedSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return Response(sz.PropertyCategoryUnifiedSerializer(category).data, status=status.HTTP_201_CREATED)
    
    def put(self, request, pk):
        try:
            category_instance = PropertyCategory.objects.get(pk=pk)
        except PropertyCategory.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = sz.PropertyCategoryUnifiedSerializer(category_instance, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return Response(sz.PropertyCategoryUnifiedSerializer(category).data, status=status.HTTP_200_OK)
        
# Api for the mobile phase
class GetCategories(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = sz.PropertyCategorySerializer
    queryset = PropertyCategory.objects.order_by('-created_at')