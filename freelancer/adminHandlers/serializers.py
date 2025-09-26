from rest_framework import serializers
from django.contrib.auth import get_user_model
from accounts.models import Role, UserRole
from .models import PropertyCategory, CategoryPricing, CategoryFeaturesField, SubCategory, FAQ, Charges
from decimal import Decimal
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
                user = User.objects.create_user(
                    first_name=validated_data['first_name'],
                    last_name=validated_data['last_name'],
                    email=validated_data['email'],
                    phone=validated_data['phone'],
                    password="00000000"
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
                    'user': user.id,
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
        
class CategoryPricingSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    category = serializers.PrimaryKeyRelatedField(required=False, queryset=PropertyCategory.objects.all())
    action = serializers.CharField(write_only=True, required=False) 
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = CategoryPricing
        fields = '__all__'
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        charges = Charges.objects.filter(for_key='regular_ad').first()
        
        charge_percent = float(charges.charge_percent) if charges else 0.00
        charge_fixed = float(charges.charge_fixed) if charges else 0.00

        price = float(representation.get('price', 0))
        discount = float(representation.get('discount', 0))

        amount = price - (price * discount) / 100
        charge = (amount * charge_percent / 100) + charge_fixed
        final_price = Decimal(amount + charge)
        
        return {
            **representation,
            "charges": charge,
            "final_price": final_price
        }

class CategoryFeaturesFieldSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    category = serializers.PrimaryKeyRelatedField(required=False, queryset=PropertyCategory.objects.all())
    action = serializers.CharField(write_only=True, required=False) 
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = CategoryFeaturesField
        fields = '__all__'
  
    
    def validate(self, data):
        """Ensure `options` is required if type is 'select'."""
        type_value = data.get("type", self.instance.type if self.instance else None)
    
        if type_value == "select" and not data.get("options"):
            raise serializers.ValidationError({"options": "This field is required when type is 'select'."})
        
        return data
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        
        lang = request.headers.get("Accept-Language", "en") if request else "en"
        
        data['label'] = instance.label_hr if lang == "hr" and instance.label_hr else instance.label_en
        
        return data
        

class SubCategorySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    category = serializers.PrimaryKeyRelatedField(required=False, queryset=PropertyCategory.objects.all())
    action = serializers.CharField(write_only=True, required=False) 
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = SubCategory
        fields = '__all__'
        
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        
        lang = request.headers.get("Accept-Language", "en") if request else "en"
        
        data['name'] = instance.name_hr if lang == "hr" and instance.name_hr else instance.name_en
        
        return data
        
class PropertyCategorySerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True,read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)  
    updated_by = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = PropertyCategory
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")

        lang = request.headers.get("Accept-Language", "en") if request else "en"

        data['name'] = instance.name_hr if lang == "hr" and instance.name_hr else instance.name_en

        return data

    def create(self, validated_data):
        return super().create({**validated_data, "created_by": self.context["request"].user})

    def update(self, instance, validated_data):
        return super().update(instance, {**validated_data, "updated_by": self.context["request"].user})

class PropertyCategoryUnifiedSerializer(serializers.ModelSerializer):   
    # Accept nested lists for pricing, features and subcategories
    category_pricing = CategoryPricingSerializer(many=True, required=False)
    category_features = CategoryFeaturesFieldSerializer(many=True, required=False)
    subcategories = SubCategorySerializer(many=True, required=False)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    updated_by = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = PropertyCategory
        fields = '__all__'
        
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")

        lang = request.headers.get("Accept-Language", "en") if request else "en"

        data['name'] = instance.name_hr if lang == "hr" and instance.name_hr else instance.name_en

        return data
    
    def create(self, validated_data):
        pricing_data = validated_data.pop('category_pricing', [])
        features_data = validated_data.pop('category_features', [])
        subcategory_data = validated_data.pop('subcategories', [])
        user = self.context['request'].user
        
        # Create a new property category
        category = PropertyCategory.objects.create(created_by=user, **validated_data)
        
        # Prepare CategoryPricing objects
        pricing_objs = [
            CategoryPricing(category=category, created_by=user, **pricing)
            for pricing in pricing_data
        ]
        if pricing_objs:
            CategoryPricing.objects.bulk_create(pricing_objs)
        
        # Prepare CategoryFeaturesField objects
        features_objs = [
            CategoryFeaturesField(category=category, created_by=user, **feature)
            for feature in features_data
        ]
        if features_objs:
            CategoryFeaturesField.objects.bulk_create(features_objs)
            
        subcategory_objs = [
            SubCategory(category=category, created_by=user, **subcategory)
            for subcategory in subcategory_data
        ]
        if subcategory_objs:
            SubCategory.objects.bulk_create(subcategory_objs)
            
        return category
    
    def update(self, instance, validated_data):

            with transaction.atomic():
                pricing_data = validated_data.pop('category_pricing', [])
                features_data = validated_data.pop('category_features', [])
                subcategory_data = validated_data.pop('subcategories', [])
                user = self.context['request'].user
                
                # Update the PropertyCategory instance
                instance.name = validated_data.get('name', instance.name)
                instance.icon = validated_data.get('icon', instance.icon)
                instance.updated_by = user
                instance.save()
            
                # Define valid actions
                valid_actions = {"update", "delete", "new"}

                def process_updates(model, data_list, instance_category):
                    new_objects = []
                    for item in data_list:
                        action = item.get('action')
                        obj_id = item.get("id")
                        print('id = ', obj_id, item)

                        if action not in valid_actions:
                            raise serializers.ValidationError({'error': f'Invalid action: {action}'})

                        if action == "update":
                            if obj_id:
                                update_data = {k: v for k, v in item.items() if k not in ['action']}
                                
                                model.objects.filter(category=instance_category, id=obj_id).update(**update_data)
                            else:
                                raise serializers.ValidationError({'error': f'ID is required for updating this item: {item}'})

                        elif action == "delete":
                            if obj_id:
                                model.objects.filter(category=instance_category, id=obj_id).delete()
                            else:
                                raise serializers.ValidationError({ 'error': f'ID is required for deletion: {item}'})

                        elif action == "new":
                            create_data = {k: v for k, v in item.items() if k not in ['action', 'id']}
                            new_objects.append(model(category=instance_category, created_by=user, **create_data))


                    if new_objects:
                        model.objects.bulk_create(new_objects)

                # Process pricing, features, and subcategories
                process_updates(CategoryPricing, pricing_data, instance)
                process_updates(CategoryFeaturesField, features_data, instance)
                process_updates(SubCategory, subcategory_data, instance)
                            
            return instance
        
class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")

        lang = request.headers.get("Accept-Language", "en") if request else "en"

        data['question'] = instance.question_hr if lang == "hr" and instance.question_hr else instance.question_en
        data['answer'] = instance.answer_hr if lang == "hr" and instance.answer_hr else instance.answer_en

        return data

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        instance = FAQ.objects.create(**validated_data)
        return instance

class ChargesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Charges
        fields = '__all__'