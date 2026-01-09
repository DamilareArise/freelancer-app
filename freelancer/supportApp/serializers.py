from rest_framework import serializers 
from .models import Conversation, Chat, SupportTicket, SupportType
from accounts.models import User
from django.db.models import Q

class ConversationSerializer(serializers.ModelSerializer):
    receiver = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    sender = serializers.PrimaryKeyRelatedField(read_only=True)
    last_message = serializers.SerializerMethodField()
    not_read_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = '__all__'
    
    
    def get_last_message(self, obj):
        last_chat = obj.chats.last()
        if last_chat:
            return {
                'message': last_chat.message,
                'created_at': last_chat.created_at,
                'sender': last_chat.sender.get_full_name,
                'is_read': last_chat.is_read
            }
        return None
    def get_not_read_count(self, obj):
        user = self.context['request'].user
        return obj.chats.filter(is_read=False).filter(~Q(sender=user)).count()
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        if instance.sender:
            representation['sender'] = {
                'id': instance.sender.id if instance.sender else None,
                'name': instance.sender.get_full_name if instance.sender else None,
                'passport': instance.sender.passport.url if instance.sender.passport else None,
            }
        
        if instance.receiver:
            representation['receiver'] = {
                'id': instance.receiver.id if instance.receiver else None,
                'name': instance.receiver.get_full_name if instance.receiver else None,
                'passport': instance.receiver.passport.url if instance.receiver.passport else None,
            }
        return representation
    
    def create(self, validated_data):
        sender = self.context['request'].user
        receiver = validated_data.get('receiver')
        
        
        if not receiver:
            raise serializers.ValidationError("Receiver is required.")
        
        existing = Conversation.objects.filter(
            Q(sender=sender, receiver=receiver) |
            Q(sender=receiver, receiver=sender)
        ).first()

        if existing:
            return existing  
        
        validated_data['sender'] = sender
        return super().create(validated_data)
    
    
class ChatSerializer(serializers.ModelSerializer):
    sender = serializers.PrimaryKeyRelatedField(read_only=True)
    conversation = serializers.PrimaryKeyRelatedField(queryset=Conversation.objects.all())
    
    class Meta:
        model = Chat
        fields = '__all__'
    
    def validate_conversation(self, value):
        user = self.context['request'].user
        
        if value.type == 'support' and user.is_admin:
            return value
        
        if value.sender != user and value.receiver != user:
            raise serializers.ValidationError("You are not a participant in this conversation.")
        return value
    
    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)
    
class SupportChatSerializer(ChatSerializer):
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['sender'] = {
            'id': instance.sender.id,
            'name': instance.sender.get_full_name,
            'passport': instance.sender.passport.url if instance.sender.passport else None,
        }
        return data

class SupportTypeSerializer(serializers.ModelSerializer):
    
    def to_representation(self, instance):
        request = self.context.get('request')
        lang = request.headers.get("Accept-Language", "en") if request else "en"
        data = super().to_representation(instance)
        if lang == "hr":
            data['name'] = instance.name_hr
            data['description'] = instance.description_hr
        else:
            data['name'] = instance.name_en
            data['description'] = instance.description_en
        return data

    class Meta:
        model = SupportType
        fields = "__all__"

class TicketSerializer(serializers.ModelSerializer):
    support_type = serializers.PrimaryKeyRelatedField(queryset=SupportType.objects.all())
    complainant = serializers.PrimaryKeyRelatedField(read_only=True)
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['complainant'] = {
            'id': instance.complainant.id,
            'name': instance.complainant.get_full_name,
            'passport': instance.complainant.passport.url if instance.complainant.passport else None,
        }
        data['support_type'] = {
            'id': instance.support_type.id,
            'name': instance.support_type.name_en or instance.support_type.name_hr,
            'description': instance.support_type.description_en or instance.support_type.description_hr,
        }
        return data
    
    class Meta:
        model = SupportTicket
        fields = '__all__'
        
    def create(self, validated_data):
        request = self.context['request']
        complainant = request.user
        validated_data['complainant'] = complainant

        # Create support ticket
        return super().create(validated_data)

class SupportConversationSerializer(serializers.ModelSerializer):
    ticket = serializers.PrimaryKeyRelatedField(queryset=SupportTicket.objects.all(), required=False)
    sender = serializers.PrimaryKeyRelatedField(read_only=True)
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = '__all__'
        
    def get_last_message(self, obj):
        last_chat = obj.chats.last()
        if last_chat:
            return {
                'message': last_chat.message,
                'created_at': last_chat.created_at,
                'sender': last_chat.sender.id,
                'is_read': last_chat.is_read
            }
        return None
        
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['sender'] = {
            'id': instance.sender.id,
            'name': instance.sender.get_full_name,
            'passport': instance.sender.passport.url if instance.sender.passport else None,
        }
        
        return data
    
    def create(self, validated_data):
        request = self.context['request']
        sender = request.user
        ticket = validated_data.pop('ticket', None)
        validated_data['type'] = 'support'
        validated_data['sender'] = sender
        
        if ticket.complainant != sender and not request.user.is_admin:
            raise serializers.ValidationError("You are not the complainant of this ticket.")
        
        if ticket.conversation:
            return ticket.conversation

        # ✅ Check if the user has a support conversation already
        existing_conversation = Conversation.objects.filter(
            Q(sender=sender) | Q(receiver=sender),
            type='support'
        ).first()

        if existing_conversation:
            
            if not ticket.conversation:
                ticket.conversation = existing_conversation
                ticket.save()
            return existing_conversation

        
        conversation = Conversation.objects.create(**validated_data)
        ticket.conversation = conversation
        ticket.save()

        return conversation

    
    
        
        
   