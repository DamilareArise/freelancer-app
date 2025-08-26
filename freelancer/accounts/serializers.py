from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Role, UserRole, Address
from django.db import transaction

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone','passport', 'is_verified', 'document_status', 'oib', 'vat', 'document_type', 'document', 'selfie', 'business_reg', 'auth_letter', 'status', 'created_at']
        
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()  # Can be email or phone
    password = serializers.CharField(write_only=True)
    

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(max_length = 68, min_length = 6, write_only = True)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'password']
        
    
    def create(self, validated_data):
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    first_name = validated_data['first_name'],
                    last_name = validated_data['last_name'],
                    email = validated_data['email'],
                    phone = validated_data['phone'],
                    password = validated_data['password'],
                )
                
                # Assign a default role (e.g., 'customer')
                customer_role = Role.objects.get(id='CUSTOMER')
                UserRole.objects.create(user=user, role=customer_role)
                
                return user
        except Exception as e:
            raise serializers.ValidationError({'error': str(e)})
        
class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'label', 'description', 'is_admin']


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'country', 'state', 'city', 'street', 'postal_code']

    def create(self, validated_data):
        user = self.context['request'].user
        
        if hasattr(user, 'address') and user.address:
            for field, value in validated_data.items():
                setattr(user.address, field, value)
            user.address.save()
            return user.address
        else:
            address = Address.objects.create(**validated_data)
            user.address = address
            user.save()
            return address