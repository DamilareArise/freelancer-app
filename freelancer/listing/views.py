from rest_framework import viewsets, status, filters
from rest_framework.permissions import IsAuthenticated
from .models import Listing, Resource, Favorite
from rest_framework.decorators import action
from . import serializers as sz
from accounts.permissions import IsAdminOrOwner, IsAdminUser, isAuthenticatedOrReadOnly
from accounts.pagination import CustomOffsetPagination
from django.db.models import Q, OuterRef, Exists, Prefetch
import json
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from adsApp.models import Ad
from django.utils.timezone import now
from paymentApp.models import CoversAllSubscription
from dateutil.relativedelta import relativedelta




# Create your views here.

class ListingViewSet(viewsets.ModelViewSet):
    """
    Handles CRUD operations for Property Listings.
    """ 
    queryset = Listing.objects.all().order_by('-created_at','-updated_at')
    serializer_class = sz.ListingSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]
    pagination_class = CustomOffsetPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
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
    queryset = Listing.objects.all()
    serializer_class = sz.ListingSerializer
    permission_classes = [isAuthenticatedOrReadOnly]
    pagination_class = CustomOffsetPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at', '-updated_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        user = self.request.user if self.request.user.is_authenticated else None

        self_param = params.get('self', 'false').lower() == 'true'
        status = params.get('status')

        #  Common annotations 
        active_ads = Ad.objects.filter(
            listing=OuterRef('pk'),
            start_date__lte=now(),
            end_date__gte=now(),
            status='active',
        )

        covers_all = CoversAllSubscription.objects.filter(
            user=OuterRef('created_by'),
            start_date__lte=now(),
            end_date__gte=now(),
        )
        
        queryset = queryset.annotate(
            has_active_ad=Exists(active_ads),
            has_covers_all=Exists(covers_all)
        )

         
        #  Base filters
        if self_param:
            filters = Q(created_by=user)

            if status in ["pending", "rejected"]:
                filters &= Q(status=status)
                
            elif status == "approved":
                filters &= Q(status='approved') & Q(has_active_ad=True) | Q(status='approved') & Q(has_covers_all=True)
                
            elif status == "expired":
                filters &= Q(status='approved') & Q(has_active_ad=False)

        else:
            filters = Q(status='approved', available=True)

        #  Dynamic filters
        if params.get('category_ids'):
            filters &= Q(category__id__in=json.loads(params['category_ids']))

        if params.get('subcategory_ids'):
            filters &= Q(subcategory__id__in=json.loads(params['subcategory_ids']))

        if params.get('country'):
            filters &= Q(location__country=params['country'])

        if params.get('city'):
            filters &= Q(location__city=params['city'])

        if params.get('county'):
            filters &= Q(location__county=params['county'])

        if params.get('price_range'):
            price_range = json.loads(params['price_range'])
            filters &= Q(price__gte=price_range[0], price__lte=price_range[1])

        queryset = queryset.filter(filters)

        #  Public listings visibility (ads OR covers-all)
        # if not self_param:
        #     queryset = queryset.filter(
        #         Q(has_active_ad=True) | Q(has_covers_all=True)
        #     )

        return queryset.distinct()



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


class Summary(APIView):
    
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Listing.objects.all() if request.user.is_admin else Listing.objects.filter(created_by=request.user)
        
        active_ads = Ad.objects.filter(
            listing=OuterRef('pk'),
            start_date__lte=now(),
            end_date__gte=now(),
            status='active',
        )
        
        covers_all = CoversAllSubscription.objects.filter(
            user=OuterRef('created_by'),
            start_date__lte=now(),
            end_date__gte=now(),
        )
        
        queryset = queryset.annotate(
            has_active_ad=Exists(active_ads),
            has_covers_all=Exists(covers_all)
        )
        
        total_count = queryset.count()
        pending_count = queryset.filter(status='pending').count()
        rejected_count = queryset.filter(status='rejected').count()
        
        approved_count = queryset.filter(
            status='approved'
        ).filter(
            Q(has_active_ad=True) | Q(has_covers_all=True)
        ).count()

        # Expired = approved AND NO active ad AND NO covers all
        expired_count = queryset.filter(
            status='approved',
            has_active_ad=False,
            has_covers_all=False
        ).count()
        
        
        data = {
            "total": total_count,
            "approved": approved_count,
            "pending": pending_count,
            "rejected": rejected_count,
            "expired": expired_count,
            # "free_listings": free_listings
        }
       
        return Response(data, status=status.HTTP_200_OK)
    
class UpdateAvailability(APIView):
    """
    Update the availability of a listing.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, listing_id):
        listing = Listing.objects.filter(id=listing_id, created_by=request.user).first()
        
        if not listing:
            return Response({"error": "Listing not found or you do not have permission to update it."}, status=status.HTTP_404_NOT_FOUND)
        
        available_raw = request.data.get('available', None)
        if available_raw is None:
            return Response({"error": "'available' field is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Normalize to boolean
        true_values = {"true", "1", True, 1}
        false_values = {"false", "0", False, 0}

        if available_raw in true_values:
            available = True
        elif available_raw in false_values:
            available = False
        else:
            return Response({"error": "Invalid value for 'available'. Must be true/false or 1/0."}, status=status.HTTP_400_BAD_REQUEST)

        listing.available = available
        listing.save()

        return Response({"message": "Availability updated successfully."}, status=status.HTTP_200_OK)
    
    

class GetSuperAdLocationListings(viewsets.ViewSet):
    permission_classes = [isAuthenticatedOrReadOnly]

    def list(self, request):
        ad_locations = request.query_params.get('locations')
        country = request.query_params.get('country')
        
        location_filter = ad_locations.split(',') if ad_locations else None
        
        ads = (
            Ad.objects.filter(
                status='active',
                type='super_ads',
                start_date__lte=now(),
                end_date__gte=now(),
                super_ads_category__isnull=False,
                listing__available = True,
                listing__status = 'approved',
                **({"listing__location__country": country} if country else {})
            )
            .select_related('listing', 'super_ads_category')
            .prefetch_related('super_ads_category__locations__app_location')
        )
        
        location_map = {}

        for ad in ads:
            listing = ad.listing
            
            category_locations = ad.super_ads_category.locations.all()

            for loc in category_locations:
                loc_id = loc.app_location.id
                
                if location_filter and loc_id not in location_filter:
                    continue
                
                serialized = sz.ListingSerializer(listing, context={'request': request}).data
                location_map.setdefault(loc_id, []).append(serialized.update({
                    "superAd": {
                        "id": ad.id
                    }
                }) or serialized)
                
        return Response(location_map, status=status.HTTP_200_OK)
    
    
class SuperadListings(viewsets.ReadOnlyModelViewSet):
    """
    Handles listing of super ads.
    """
    serializer_class = sz.ListingSerializer
    permission_classes = [IsAdminUser]
    pagination_class = CustomOffsetPagination
    
    def get_queryset(self):
        """
        Filter super ads based on various parameters.
        """
        params = self.request.query_params
        search = params.get("search")
        payment_status = params.get('payment_status')
        ad_type = params.get('ad_type')
        provider_id = params.get('provider')
        
        # Initialize queryset
        queryset = Listing.objects.filter(ads__type = 'super_ads').prefetch_related(
            Prefetch('ads', queryset=Ad.objects.filter(type='super_ads').prefetch_related('impressions')),
            'payments'
        ).order_by('-created_at', '-updated_at')
        
        # Initialize filters with an empty Q object
        filters = Q()
        if search:
            filters &= Q(category__name__icontains=search) | \
                    Q(service__description_en__icontains=search) | \
                    Q(service__description_hr__icontains=search) | \
                    Q(service__header__icontains=search)
        if payment_status:
            filters &= Q(payments__status__in=payment_status.split(","))
        if ad_type:
            filters &= Q(ads__super_ads_category__id__in=ad_type.split(","))
        if provider_id:
            filters &= Q(created_by__id=provider_id)
            
        # Apply the accumulated filters in one go
        return queryset.filter(filters).distinct()


class AvailableListingsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Returns available and approved listings in random order.
    """
    serializer_class = sz.ListingSerializer
    permission_classes = [isAuthenticatedOrReadOnly]
    pagination_class = CustomOffsetPagination

    def get_queryset(self):
        return Listing.objects.filter(status='approved', available=True).order_by('?')
