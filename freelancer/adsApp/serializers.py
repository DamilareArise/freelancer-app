from rest_framework import serializers
from .models import SuperAdsCategory, AppLocation, SuperAdsCategoryLocation, Ad, Impression
from django.db import transaction
from datetime import datetime
from adminHandlers.models import CategoryPricing, Charges
from dateutil.relativedelta import relativedelta


class SuperAdsCategorySerializer(serializers.ModelSerializer):
    locations = serializers.ListField(child=serializers.CharField(), write_only=True)

    class Meta:
        model = SuperAdsCategory
        fields = ['id', 'title', 'price', 'tier', 'features', 'locations']
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['locations'] = list(
            {
                'id': location.app_location_id,
                'name': location.app_location.name
            }
            for location in instance.locations.all()
        )
        
        # fetch super_ad charges
        charges = Charges.objects.filter(for_key='super_ad').first()
        charge_percent = float(charges.charge_percent) if charges else 0.0
        charge_fixed = float(charges.charge_fixed) if charges else 0.0
        price = float(representation.get('price', 0.0))
        price_charges = (price * charge_percent / 100) + charge_fixed
        total_price = price + price_charges
        
        representation['total_price'] = total_price
        representation['charges'] = price_charges
        
        return representation
        
    def create(self, validated_data):
        try:
            with transaction.atomic():
                locations = validated_data.pop('locations', [])
                instance = super().create(validated_data)
                
                location_objects = [
                    SuperAdsCategoryLocation(super_ads_category=instance, app_location_id=location)
                    for location in locations
                ]
                SuperAdsCategoryLocation.objects.bulk_create(location_objects)
        
                return instance
        except Exception as e:
            raise serializers.ValidationError({'error': f'Failed to create super ads category: {str(e)}'})
        
    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                locations = validated_data.pop('locations', [])
                instance = super().update(instance, validated_data)
                
                existing_location_ids = set(
                    SuperAdsCategoryLocation.objects.filter(
                        super_ads_category=instance
                    ).values_list('app_location_id', flat=True)
                )
                new_location_ids = set(location for location in locations)
                print(new_location_ids, 'new_location_ids')

                # Delete only the removed locations
                locations_to_delete = existing_location_ids - new_location_ids
                SuperAdsCategoryLocation.objects.filter(
                    super_ads_category=instance, app_location_id__in=locations_to_delete
                ).delete()

                # Insert only the new locations
                locations_to_create = new_location_ids - existing_location_ids
                SuperAdsCategoryLocation.objects.bulk_create([
                    SuperAdsCategoryLocation(super_ads_category=instance, app_location_id=location_id)
                    for location_id in locations_to_create
                ])
                
                return instance
        except Exception as e:
            raise serializers.ValidationError({'error': f'Failed to update super ads category: {str(e)}'})
                 
class AppLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppLocation
        fields = ['id', 'name']

class SuperAdsCategoryLocationSerializer(serializers.ModelSerializer):
    super_ads_category = serializers.PrimaryKeyRelatedField(queryset=SuperAdsCategory.objects.all())
    app_location = serializers.PrimaryKeyRelatedField(queryset=AppLocation.objects.all())

    class Meta:
        model = SuperAdsCategoryLocation
        fields = ['id', 'super_ads_category', 'app_location'] 
    
    def validate(self, data):
        super_ads_category = data.get('super_ads_category')
        app_location = data.get('app_location')
        
        if SuperAdsCategoryLocation.objects.filter(super_ads_category=super_ads_category, app_location=app_location).exists():
            raise serializers.ValidationError("SuperAdsCategoryLocation already exists")
        
        return data

class AdSerializer(serializers.ModelSerializer):
    super_ads_category = serializers.PrimaryKeyRelatedField(queryset=SuperAdsCategory.objects.all(), required=False)
    category_price_id = serializers.PrimaryKeyRelatedField(
        queryset=CategoryPricing.objects.all(),
        write_only = True
    )
    
    class Meta:
        model = Ad
        fields = '__all__'
        read_only_fields = ('start_date', 'end_date', 'status')
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.super_ads_category:
            representation['super_ads_category'] = {
                "id": instance.super_ads_category_id,
                "title": instance.super_ads_category.title,
                "tier": instance.super_ads_category.tier
            }
        return representation

    def create(self, validated_data):
        category_price = validated_data.pop('category_price_id', None)
        if category_price and category_price.duration:
            # Calculate end date based on duration
            start_date = datetime.now()
            end_date = start_date + relativedelta(months=category_price.duration)
            validated_data['end_date'] = end_date
            validated_data['start_date'] = start_date
            validated_data['status'] = 'active'
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        category_price = validated_data.pop('category_price_id', None)
        if category_price and category_price.duration:
            # Update end date based on new duration
            start_date = instance.start_date
            end_date = start_date + relativedelta(months=category_price.duration)
            validated_data['end_date'] = end_date
        
        return super().update(instance, validated_data)
    
class ImpressionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Impression
        fields = '__all__'
        
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        
        # Ensure that the type is either 'impression' or 'click'
        if validated_data['type'] not in ['impression', 'click']:
            raise serializers.ValidationError("Type must be either 'impression' or 'click'")
        
        return super().create(validated_data)