from rest_framework import serializers
from listing.serializers import ListingMinimalSerializer
from .models import Payment




class PaymentSerializer(serializers.ModelSerializer):
    listing = ListingMinimalSerializer()
    due_date = serializers.SerializerMethodField()
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Payment
        fields = ['id', 'status', 'transaction_id', 'due_date', 'amount_paid', 'listing', 'created_at', 'updated_at']
        
    def get_due_date(self, obj):
        ads = obj.listing.ads.all()
        latest_ad = ads[0] if ads else None
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