from rest_framework import serializers
from .models import Availability, Booking, Reviews
import datetime
from listing.serializers import ListingMinimalSerializer
from listing.models import Listing
from accounts.tasks import send_email
from notificationApp.models import Notification



class TimeOnlyField(serializers.Field):
    def to_internal_value(self, value):
        if not isinstance(value, str):
            raise serializers.ValidationError("Time must be a string in 'HH:MM' format.")
        try:
            return datetime.datetime.strptime(value, "%H:%M").time()
        except ValueError:
            raise serializers.ValidationError("Invalid time format. Expected 'HH:MM'.")

    def to_representation(self, value):
        if isinstance(value, datetime.time):
            return value.strftime("%H:%M")
        return value

class AvailableSerializer(serializers.ModelSerializer):
    slots = serializers.ListField(child=TimeOnlyField())
    
    class Meta:
        model = Availability
        fields = ["id", 'day', 'slots']
        
    def create(self, validated_data):
        user = self.context['request'].user
        day = validated_data.get('day')
        
        # Convert time objects to strings before saving
        slots = validated_data.get('slots')
        slot_strings = [t.strftime("%H:%M") for t in slots]
        
        if Availability.objects.filter(user=user, day=day).exists():
            # update the slots if the date already exists
            availability = Availability.objects.get(user=user, day=day)
            availability.slots = slot_strings
            availability.save()
            return availability
        else:
            # create a new availability record
            validated_data['slots'] = slot_strings
            availability = Availability.objects.create(user=user, **validated_data)
            return availability
    
class BookingSerializer(serializers.ModelSerializer):
    listing = serializers.PrimaryKeyRelatedField(queryset=Listing.objects.all())
    
    def validate(self, data):
        date_time = data.get('date_time')
        listing = data['listing']
        provider = listing.created_by

        if not isinstance(date_time, datetime.datetime):
            raise serializers.ValidationError("Invalid date_time. Must be a valid datetime object.")

        weekday = date_time.strftime("%A").lower()

        try:
            availability = Availability.objects.get(user=provider, day=weekday)
        except Availability.DoesNotExist:
            raise serializers.ValidationError({'error': "The provider is not available on this day."})

        slots = availability.slots or []
        time_str = date_time.strftime("%H:%M")

        if time_str not in slots:
            raise serializers.ValidationError({'error': "The provider is not available at this time."})

        return data
    
    def to_representation(self, instance):
        rep = super().to_representation(instance) 
        requester = getattr(instance, "requester", None)
        if requester:
            passport_url = requester.passport.url if requester.passport else None
            rep['requester'] = {
                'id': requester.id,
                'first_name': requester.first_name,
                'last_name': requester.last_name,
                'passport': passport_url,
                'email': requester.email,
                'phone': requester.phone,
            }
        else:
            rep['requester'] = None
        
        rep['listing'] = ListingMinimalSerializer(instance.listing, context=self.context).data
        
        
        return rep


    class Meta:
        model = Booking
        fields = ['id', 'listing', 'date_time', 'status', 'requester', 'contact_name', 'contact_phone', 'note', 'created_at', 'updated_at']
        read_only_fields = ['requester']
        
        
    def create(self, validated_data):
        booking = super().create(validated_data) 
        
        context_req = {
            'subject': 'Successful Booking',
            "user": booking.requester.id,
            "booking": booking.id
        }
        context_lister ={
            'subject': 'New Booking',
            "user": booking.listing.created_by.id,
            "booking": booking.id
        }
        
        send_email.delay(context_req, 'booking-made-customer.html')
        send_email.delay(context_lister, 'booking-made-provider.html')
        
        # IN-APP NOTIFICATIONS
        Notification.objects.create(
            recipient_user=booking.requester,
            title="Booking Successful",
            message=f"You successfully booked {booking.listing.title}.",
            data={"booking_id": booking.id},
            status=Notification.Status.SENT
        )

        Notification.objects.create(
            recipient_user=booking.listing.created_by,
            title="New Booking",
            message=f"You received a new booking from {booking.requester.get_full_name}.",
            data={"booking_id": booking.id},
            status=Notification.Status.SENT
        )
        
        return booking


class ReviewSerializer(serializers.ModelSerializer):
    booking = serializers.PrimaryKeyRelatedField(queryset=Booking.objects.all())
    
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        
        rep['reviewer'] = {
            'id': instance.reviewer.id,
            'first_name': instance.reviewer.first_name,
            'last_name': instance.reviewer.last_name,
            'passport': instance.reviewer.passport.url if instance.reviewer.passport else None,
        }
        return rep
    
    class Meta:
        model = Reviews
        fields = ['id', 'booking', 'reviewer', 'rating', 'comment', 'impression', 'created_at']
        read_only_fields = ['reviewer', 'created_at']