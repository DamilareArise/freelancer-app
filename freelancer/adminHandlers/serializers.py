from rest_framework import serializers
from django.contrib.auth import get_user_model
from accounts.models import Role, UserRole
from django.db import transaction
from accounts.tasks import send_email

User = get_user_model()

class AdminSerializer(serializers.ModelSerializer):
    roles = serializers.ListField(child=serializers.CharField(), write_only=True)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'roles']

    def to_representation(self, instance):
        """Customize the representation to include roles."""
        representation = super().to_representation(instance)
        representation['roles'] = list(instance.user_roles.values_list('role_id', flat=True))
        return representation

    def create(self, validated_data):
        """Create user and assign roles."""
        roles = validated_data.pop('roles', []) 

        try:
            with transaction.atomic():  # Start an atomic transaction
                user = User.objects.create_admin(
                    first_name=validated_data['first_name'],
                    last_name=validated_data['last_name'],
                    email=validated_data['email'],
                    phone=validated_data['phone']
                )

                # Assign roles to the user
                UserRole.objects.bulk_create([
                    UserRole(user=user, role_id=role_id) for role_id in roles
                ])
                
                # send mail to admin
                subject = "Admin Account Created"
                role_ids = user.user_roles.values_list('role_id', flat=True) 
                roles = Role.objects.filter(id__in=role_ids)

                context = {
                    'subject': subject,
                    'email': user.email,
                    "first_name": user.first_name,
                    'link': f'https://admin.book-freelancer.com/reset-password-otp/?email={user.email}',
                    'roles': list(roles.values_list('label', flat=True)),
                }
                send_email.delay(context, file='admin_onboarding.html')

            return user 

        except Exception as e:
            raise serializers.ValidationError({'error': f'Failed to create user and assign roles: {str(e)}'})
        
    def update(self, instance, validated_data):
        """Update user and assign roles."""
        roles = validated_data.pop('roles', []) 
        try:
            with transaction.atomic():  # Start an atomic transaction
                instance.first_name = validated_data['first_name']
                instance.last_name = validated_data['last_name']
                instance.email = validated_data['email']
                instance.phone = validated_data['phone']
                instance.save()    
            
                existing_role_ids = set(instance.user_roles.values_list('role_id', flat=True))
                new_role_ids = set(roles)

                # Delete only the removed roles
                roles_to_delete = existing_role_ids - new_role_ids
                UserRole.objects.filter(
                    user=instance, role_id__in=roles_to_delete
                ).delete()

                # Insert only the new roles
                roles_to_create = new_role_ids - existing_role_ids
                UserRole.objects.bulk_create([
                    UserRole(user=instance, role_id=role_id) for role_id in roles_to_create
                ])
                
                return instance  
        except Exception as e:
            raise serializers.ValidationError({'error': f'Failed to update user and assign roles: {str(e)}'})
        
