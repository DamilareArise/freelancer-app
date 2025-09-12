from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from .models import Listing, Resource, Favorite
from rest_framework.decorators import action
from .  import serializers as sz
from accounts.permissions import IsAdminOrOwner
from accounts.pagination import CustomOffsetPagination
from django.db.models import Q
import json
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response



# Create your views here.

class ListingViewSet(viewsets.ModelViewSet):
    """
    Handles CRUD operations for Property Listings.
    """ 
    queryset = Listing.objects.all().order_by('-created_at','-updated_at')
    serializer_class = sz.ListingSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]
    pagination_class = CustomOffsetPagination
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """
        Filter property listings based on various parameters including user.
        """
        
        queryset = super().get_queryset()
        params = self.request.query_params
        search = params.get("search")
        status = params.get('status')
        category_ids = params.get('category_ids')
        price_range = params.get('price_range')
        subcategory_ids = params.get('subcategory_ids')
        country = params.get('country')
        
        # Initialize filters with an empty Q object
        filters = Q()

        if search:
            filters &= Q(category__name__icontains=search) | \
                    Q(property__description_en__icontains=search) | \
                    Q(property__description_hr__icontains=search) | \
                    Q(property__header__icontains=search)

        if status in ["pending", "approved", "rejected"]:
            filters &= Q(status=status)

        if category_ids:
            filters &= Q(category__id__in=json.loads(category_ids))

        if price_range:
            price_range = json.loads(price_range)
            filters &= Q(price__gte=price_range[0], price__lte=price_range[1])

        if subcategory_ids:
            filters &= Q(subcategory__id__in=json.loads(subcategory_ids))
        
        if country:
            filters &= Q(location__country__icontains = country)

        # Apply the accumulated filters in one go
        return queryset.filter(filters)
    
    def list(self, request, *args, **kwargs):
        """
        Returns a list of listings along with counts of pending and rejected listings.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        # Count pending and rejected listings
        pending_count = Listing.objects.filter(status="pending").count()
        rejected_count = Listing.objects.filter(status="rejected").count()

        extra_data = {
        "pending_count": pending_count,
        "rejected_count": rejected_count
        }

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.paginator.get_paginated_response(serializer.data, extra_data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "listings": serializer.data,
            **extra_data  
        }, status=status.HTTP_200_OK)    

    def create(self, request, *args, **kwargs):
        """
        Handle nested object creation.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = serializer.save()
        data = {
            "listing_id": listing.id,
            "message": "Listing created successfully",
            "status": True
        }
        return Response(data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        Handle nested object updates.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        listing = serializer.save()
        listing.status = 'pending'
        listing.save()
        data = {
            "listing_id": listing.id,
            "message": "Listing updated successfully",
            "status": True
        }
        return Response(data, status=status.HTTP_200_OK)
    

# All listings for the user end(mobile app)  
class UserListings(viewsets.ReadOnlyModelViewSet):
    queryset = Listing.objects.all().order_by('-created_at','-updated_at')
    serializer_class = sz.ListingSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomOffsetPagination
    
    
    def get_queryset(self):
        
        queryset = super().get_queryset()
        params = self.request.query_params
        user = self.request.user
        category_ids = params.get('category_ids')
        subcategory_ids = params.get('subcategory_ids')
        country =  params.get('country')
        city = params.get('city')
        county = params.get('county')
        price_range = params.get('price_range')
        self_param = params.get('self', 'false').lower() == 'true'
        status = params.get('status')
        
        
        # Base filter: Show only the current user's listings if self=true
        if self_param:
            filters = Q(created_by=user)
            if status in ["pending", "approved", "rejected"]:
                filters &= Q(status=status)
        else:
            filters = Q(status='approved')  

        # Add filters dynamically
        if category_ids:
            filters &= Q(category__id__in=json.loads(category_ids))
        
        if subcategory_ids:
            filters &= Q(subcategory__id__in=json.loads(subcategory_ids))
        
        if country:
            filters &= Q(location__country=country)
        
        if city:
            filters &= Q(location__city=city)
        
        if county:
            filters &= Q(location__county=county)
        
        if price_range:
            price_range = json.loads(price_range)
            filters &= Q(price__gte=price_range[0], price__lte=price_range[1])

    
        return queryset.filter(filters).distinct()
            

    def list(self, request, *args, **kwargs):
        
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.paginator.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResourceViewSet(viewsets.ModelViewSet):
    """
    Handles CRUD operations for Listing Resources (Images, Videos).
    """
    queryset = Resource.objects.all()
    serializer_class = sz.ResourceSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser) 

    def create(self, request, *args, **kwargs):
        listing_id = request.data.get("listing")

        # Validate if the listing exists before proceeding
        if not listing_id:
            return Response({"error": "Listing ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    
class FavoriteViewset(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = sz.FavoriteSerializer
    
    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def toggle_favorite(self, request):
        listing_id = request.data.get("listing")
        listing = Listing.objects.filter(id=listing_id).first()
        
        if not listing:
            return Response({"error": "Listing not found"}, status=status.HTTP_404_NOT_FOUND)

        favorite = Favorite.objects.filter(user=request.user, listing=listing).first()

        if favorite:
            favorite.delete()
            return Response({"message": "Removed from favorites"}, status=status.HTTP_204_NO_CONTENT)
        else:
            favorite = Favorite.objects.create(user=request.user, listing=listing)
            return Response(sz.FavoriteSerializer(favorite).data, status=status.HTTP_201_CREATED)


class GetFavoritedListings(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = sz.ListingSerializer
    
    def get_queryset(self):
        return Listing.objects.filter(
            id__in=Favorite.objects.filter(user=self.request.user).values_list('listing_id', flat=True)
        )
        
        