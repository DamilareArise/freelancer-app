from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets , mixins, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Availability, Booking, Reviews
from .serializers import AvailableSerializer, BookingSerializer, ReviewSerializer
from rest_framework.views import APIView
from listing.models import Listing
from django.db.models import Q, Avg, Count
from rest_framework.decorators import action
from accounts.tasks import send_email
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError


class AvailableViewSet(viewsets.ModelViewSet):
    queryset = Availability.objects.all()
    serializer_class = AvailableSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(user=user)
   
    
class GetUserAvailability(APIView):
    serializer_class = AvailableSerializer
    permission_classes = [IsAuthenticated]
    def get(self, request, listing_id):
        listing = get_object_or_404(Listing, id=listing_id)
        availability = Availability.objects.filter(user=listing.created_by)
        serializer = AvailableSerializer(availability, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [ filters.OrderingFilter ]
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params
        status = params.get('status')
        search = params.get('search')
        queryset = self.queryset.filter(requester=user)
        
        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(
                Q(listing__service__header__icontains=search) | 
                Q(listing__created_by__first_name__icontains=search) |
                Q(listing__created_by__last_name__icontains=search) |
                Q(listing__location__city__icontains=search) |
                Q(listing__location__country__icontains=search) |
                Q(listing__location__county__icontains=search) 
            )
            
        return queryset
        
    def perform_create(self, serializer):
        serializer.save(requester=self.request.user)
    
    def perform_update(self, serializer):
        booking = self.get_object()
        if booking.requester != self.request.user:
            return Response({"error": "You do not have permission to update this booking."}, status=status.HTTP_403_FORBIDDEN)
        serializer.save()
        
class BookingManagementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset.filter(listing__created_by=user)
        params = self.request.query_params
        status = params.get('status')
        search = params.get('search')
        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(
                Q(listing__service__header__icontains=search) | 
                Q(requester__first_name__icontains=search) |
                Q(requester__last_name__icontains=search) |
                Q(listing__location__city__icontains=search) |
                Q(listing__location__country__icontains=search) |
                Q(listing__location__county__icontains=search) 
            )
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['patch'], url_path='update-status')    
    def update_status(self, request, pk=None):
        booking = get_object_or_404(Booking, pk=pk)
        new_status = request.data.get('status')
        
        if booking.listing.created_by != request.user:
            return Response({"error": "You do not have permission to update this booking."}, status=status.HTTP_403_FORBIDDEN)
                
        if new_status:
            if new_status not in ['rejected', 'confirmed']:
                return Response({"error": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)
            booking.status = new_status

            template = None
            if new_status == 'confirmed':
                template = "booking-confirmed.html"
            elif new_status == 'rejected':
                template = "booking-rejected.html"
               
                
            context = {
                "subject": "Booking Status Update",
                "user": booking.requester.id,
                "booking": booking.id,
            }
            
            booking.save()
            send_email.delay(context, template)

            return Response({"status": "Booking status updated successfully."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Status is required."}, status=status.HTTP_400_BAD_REQUEST)
        
    
    @action(detail=False, methods=['get'], url_path='get-status-counts')
    def get_status_counts(self, request):
        user = request.user
        bookings = Booking.objects.filter(listing__created_by=user)
        
        status_counts = {
            'pending': bookings.filter(status='pending').count(),
            'confirmed': bookings.filter(status='confirmed').count(),
            'completed': bookings.filter(status='completed').count(),
            'canceled': bookings.filter(status='canceled').count(),
            'rejected': bookings.filter(status='rejected').count(),
        }
        
        return Response(status_counts, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['patch'], url_path='cancel')    
    def cancel_booking(self, request, pk=None):
        """
        Allow the requester to cancel their own booking.
        """
        booking = get_object_or_404(Booking, pk=pk)
        cancel_reason = request.data.get('cancel_reason', '')
        if not cancel_reason:
            return Response({"error": "Cancel reason is required."}, status=status.HTTP_400_BAD_REQUEST)

        if booking.requester != request.user:
            return Response({"error": "You are not the owner of this booking."}, status=status.HTTP_403_FORBIDDEN)

        if booking.status == "canceled":
            return Response({"error": "Booking is already canceled."}, status=status.HTTP_400_BAD_REQUEST)

        
        if booking.status in ["completed", "rejected"]:
            return Response({"error": f"Cannot cancel a {booking.status} booking."}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = "canceled"
        booking.canceled_at = timezone.now()
        booking.canceled_by = request.user
        booking.cancel_reason = cancel_reason

        # Notify the provider about the cancellation
        context = {
            "subject": "Booking Canceled",
            "user": booking.listing.created_by.id,
            "booking": booking.id,
        }
        
        
        response = {}
        
        booking.save()
        send_email.delay(context, "booking-canceled.html")
        response.update({"status": "Booking canceled successfully."})
        return Response(response, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='complete_booking')    
    def complete_booking(self, request, pk=None):
        """
        Allow the requester to mark their booking as completed.
        """
        booking = get_object_or_404(Booking, pk=pk)
        if booking.requester != request.user:
            return Response({"error": "You are not the owner of this booking."}, status=status.HTTP_403_FORBIDDEN)
        if booking.status != "confirmed":
            return Response({"error": "Booking must be confirmed to be completed."}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = "completed"
        booking.save()
                
        # Notify the provider about the completion
        context = {
            "subject": "Booking Completed",
            "user": booking.listing.created_by.id,
            "booking": booking.id,
        }
        send_email.delay(context, "booking-completed.html")
        
        return Response({"status": "Booking status updated successfully."}, status=status.HTTP_200_OK)
        
        
class ReviewViewSet(mixins.CreateModelMixin,
                    mixins.UpdateModelMixin,
                    viewsets.GenericViewSet):
    queryset = Reviews.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        booking_id = self.request.data.get('booking')
        booking = get_object_or_404(Booking, id=booking_id)
        
        if booking.requester != self.request.user:
            raise PermissionDenied("You can only review your own bookings.")
        
        if Reviews.objects.filter(booking=booking, reviewer=self.request.user).exists():
            raise ValidationError("You have already reviewed this booking.")
        
        serializer.save(reviewer=self.request.user, booking=booking)
        
class GetReviews(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, listing_id):
        """
        Get all reviews for a specific listing.
        """
        params = request.query_params
        fetch_all = params.get('all', 'false').lower() == 'true'
        
        
        listing = get_object_or_404(Listing, id=listing_id)
        bookings = Booking.objects.filter(listing=listing)
        reviews = Reviews.objects.filter(booking__in=bookings)
        
        # Review summary computation
        total_reviews = reviews.count()
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        
        star_counts = reviews.values('rating').annotate(count=Count('id'))
        star_dist = {i: 0 for i in range(1, 6)}
        for item in star_counts:
            star_dist[item['rating']] = item['count']

        if not fetch_all:
            reviews = reviews.filter(rating__gte=3)
            reviews = reviews.order_by('-created_at')[:3]
            
        if not reviews.exists():
            return Response({"message": "No reviews found for this listing."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ReviewSerializer(reviews, many=True)
        
        return Response({
            "summary": {
                "average": round(avg_rating, 1),
                "total_reviews": total_reviews,
                "stars": star_dist,
            },
            "reviews": serializer.data
        }, status=status.HTTP_200_OK)
        