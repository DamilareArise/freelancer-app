from rest_framework import serializers
from listing.serializers import ListingMinimalSerializer
from .models import Payment, CoversAllSubscription
from django.utils import timezone




class PaymentSerializer(serializers.ModelSerializer):
    listing = ListingMinimalSerializer(allow_null=True)
    due_date = serializers.SerializerMethodField()
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    payment_type = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id',
            'payment_type',
            'status',
            'transaction_id',
            'due_date',
            'amount_paid',
            'listing',
            'created_at',
            'updated_at',
        ]

    def get_payment_type(self, obj):
        if obj.covers_all:
            return 'covers_all'
        if obj.super_ad:
            return 'super_ads'
        return 'regular_ads'

    def get_due_date(self, obj):
     
        # Covers-all payments
        if obj.covers_all:
            return obj.due_date

        # listing may be None
        if not obj.listing:
            return None

        # Regular ads
        latest_ad = obj.listing.ads.order_by('-end_date').first()
        return latest_ad.end_date if latest_ad else None

    
    
class PaymentSerializerForSuperAd(serializers.ModelSerializer):
    listing = ListingMinimalSerializer()
    due_date = serializers.SerializerMethodField()
    super_ads = serializers.SerializerMethodField()
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'status', 'transaction_id', 'due_date', 'amount_paid', 'super_ads', 'listing', 'created_at', 'updated_at']

    def get_due_date(self, obj):
        latest_super_ad = obj.listing.ads.filter(type='super_ads').order_by('-end_date').first()
        return latest_super_ad.end_date if latest_super_ad else None

    def get_super_ads(self, obj):
        if obj.super_ad:
            return {
                'tier': obj.super_ad.tier,
                'price': obj.super_ad.price,
                'is_active': False  
            }

        # Optional: fallback to Ad if you want to check activation
        latest_super_ad = obj.listing.ads.filter(type='super_ads').order_by('-end_date').first()
        if latest_super_ad and latest_super_ad.super_ads_category:
            return {
                'id': latest_super_ad.id,
                'tier': latest_super_ad.super_ads_category.tier,
                'price': latest_super_ad.super_ads_category.price,
                'is_active': latest_super_ad.is_active,
            }

        return None
    

class CoversAllSubscriptionSerializer(serializers.ModelSerializer):
    is_active = serializers.SerializerMethodField()
    remaining_days = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()

    class Meta:
        model = CoversAllSubscription
        fields = [
            "id",
            "start_date",
            "end_date",
            "is_active",
            "remaining_days",
            "payment",
        ]

    def get_is_active(self, obj):
        now = timezone.now()
        return obj.start_date <= now <= obj.end_date

    def get_remaining_days(self, obj):
        now = timezone.now()
        if obj.end_date < now:
            return 0
        return (obj.end_date - now).days

    def get_payment(self, obj):
        if not obj.payment:
            return None

        return {
            "id": obj.payment.id,
            "net_amount": obj.payment.net_amount,
            "amount_paid": obj.payment.amount_paid,
            "status": obj.payment.status,
            "months": obj.payment.covers_all_month,
            "transaction_id": obj.payment.transaction_id,
            "created_at": obj.payment.created_at,
        }