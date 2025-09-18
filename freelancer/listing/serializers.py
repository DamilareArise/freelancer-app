from rest_framework import serializers
from .models import (Listing, Favorite, Location, Service, Contact, Resource, ListingFeatures, CategoryFeaturesField)
from accounts.serializers import UserSerializer
from adminHandlers.models import PropertyCategory
from accounts.tasks import send_email



class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ['id', 'user', 'listing']
        read_only_fields = ['user']

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'
        
class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'
        
class ResourceSerializer(serializers.ModelSerializer):
    listing = serializers.PrimaryKeyRelatedField(queryset=Listing.objects.all())

    class Meta:
        model = Resource
        fields = '__all__'
        extra_kwargs = {
            'resource': {'required': False}
        }

class NestedResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        exclude = ["listing"]  

class ListingFeatureSerializer(serializers.ModelSerializer):
    feature_field = serializers.PrimaryKeyRelatedField(queryset=CategoryFeaturesField.objects.all())
    type = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()
    
    class Meta:
        model = ListingFeatures
        fields = ['feature_field', 'value', 'type', 'label', 'unit']
        
    def get_type(self, obj):
        return obj.feature_field.type if obj.feature_field else None
    
    def get_label(self, obj):
        return obj.feature_field.label if obj.feature_field else None

    def get_unit(self, obj):
        return obj.feature_field.unit if obj.feature_field else None
    
    
class ListingSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    location = LocationSerializer()
    service = ServiceSerializer()
    contact = ContactSerializer()
    resources = NestedResourceSerializer(many=True, required=False)
    category = serializers.PrimaryKeyRelatedField(queryset=PropertyCategory.objects.all())
    features = ListingFeatureSerializer(many=True, required=False)
    

    class Meta:
        model = Listing
        fields = '__all__'
        
    def to_representation(self, instance):
        """
        Customize how the listing is serialized by attaching the latest regular, super ad and favorite
        """
        representation = super().to_representation(instance)
        
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            # Check if this listing is favorited by the user
            is_favorited = Favorite.objects.filter(user=request.user, listing=instance).exists()
            representation['favorite'] = is_favorited
        else:
            representation['favorite'] = False
            
        return representation

    def create(self, validated_data):
        """
        Custom create method to handle nested location, property, and features.
        """
        request = self.context['request']
        user = request.user
        
        location_data = validated_data.pop('location')
        service_data = validated_data.pop('service')
        contact_data = validated_data.pop('contact') 
        features_data = validated_data.pop('features', [])
        resources_data = validated_data.pop('resources', [])
                
        location = Location.objects.create(**location_data)
        service_obj = Service.objects.create(**service_data)
        contact_obj = Contact.objects.create(**contact_data)

        listing = Listing.objects.create(
            created_by=user,
            location=location,
            property=service_obj,
            contact=contact_obj,
            **validated_data
        )
        
        # Save property features dynamically
        for feature in features_data:
            ListingFeatures.objects.create(listing=listing, **feature)
            
        for resource in resources_data:
            Resource.objects.create(listing=listing, **resource)
        
        context = {
            "subject": 'New Listing Created',
            'listing': listing,
            'user': user,
        }
        
        # send_email.delay(context, file='pending.html')
            
        return listing
    
    def update(self, instance, validated_data):
        """
        Custom update method for nested serializers.
        """
        location_data = validated_data.pop('location', None)
        service_data = validated_data.pop('service', None)
        contact_data = validated_data.pop('contact', None)
        features_data = validated_data.pop('features', None)
        
        
        if location_data:
            for key, value in location_data.items():
                setattr(instance.location, key, value)
            instance.location.save()

        if service_data:
            for key, value in service_data.items():
                setattr(instance.property, key, value)
            instance.property.save()
            
        if contact_data:
            for key, value in contact_data.items():
                setattr(instance.contact, key, value)
            instance.contact.save()    
            
        if features_data is not None:
            instance.features.all().delete()  # Clear old features
            for feature in features_data:
                ListingFeatures.objects.create(listing=instance, **feature)
             
        if 'resources' in validated_data:
            new_resources_data = validated_data.pop('resources')

            instance.resources.all().delete()

            for resource_data in new_resources_data:
                Resource.objects.create(listing=instance, **resource_data)

        return super().update(instance, validated_data)