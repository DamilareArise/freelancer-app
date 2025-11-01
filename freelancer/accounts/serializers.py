from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Role, UserRole, Address
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken
from .tasks import send_email

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    
    def to_representation(self, instance):
        user = super().to_representation(instance)
        user['roles'] = [role.role.label for role in instance.user_roles.all()] if instance.user_roles.exists() else []
        user['address'] = AddressSerializer(instance.address).data if instance.address else None
        return user

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone','passport', 'is_verified', 'document_status', 'oib', 'vat', 'document_type', 'document_front', 'document_back', 'certificate', 'selfie', 'business_reg', 'auth_letter', 'status', 'created_at']
        
        
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
    country_name = serializers.CharField(source='country.name', read_only=True)

    class Meta:
        model = Address
        fields = ['id', 'country', 'state', 'city', 'street', 'postal_code', 'country_name']


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
        
def get_tokens_for_user(user):
    """
    Generate JWT tokens for a user.
    """
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
    
class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=4, min_length=4, write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """Ensure the email exists in the database."""
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user found with this email.")
        return value

class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    
    def validate(self, data):
        """Validate the new password and confirm password."""
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")
        
        if new_password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        
        return data
    
class DocumentSerializer(serializers.ModelSerializer):
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), write_only =True)
    class Meta:
        model = User
        fields = ['oib', 'vat', 'document_type', 'document_front', 'document_back', 'certificate', 'selfie', 'business_reg', 'auth_letter', 'auth_letter', 'role']
        
    def update(self, instance, validated_data):
        user = instance
        role = validated_data.pop('role')
        
        if not role:
            raise serializers.ValidationError({"error": "Role is required."})
        
        if role.id == 'SERVICE_PROVIDER' and user.document_status == 'submitted' and user.user_roles.filter(role__id='SERVICE_PROVIDER').exists():
            raise serializers.ValidationError({"error": "Document has already been submitted."})
        
        for attr, value in validated_data.items():
            setattr(user, attr, value)
        
        user.document_status = 'submitted'  
        user.save()
        
        
        UserRole.objects.get_or_create(user=user, role=role)
        
        # Assign CUSTOMER role by default
        try:
            customer_role = Role.objects.get(id='CUSTOMER')
            UserRole.objects.get_or_create(user=user, role=customer_role)
        except Role.DoesNotExist:
            raise serializers.ValidationError({"error": "Default CUSTOMER role not found."})
        
        context = {
            "subject": "Document updated",
            "user": user.id,
            "role": role.label,
        }
        send_email.delay(context, file='seller_onboarding.html')
        return user

