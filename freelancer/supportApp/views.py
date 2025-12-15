from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets
from .models import Conversation, Chat, SupportTicket, SupportType
from .serializers import ConversationSerializer, ChatSerializer, TicketSerializer, SupportTypeSerializer, SupportConversationSerializer, SupportChatSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Q, Max
from rest_framework import status
from accounts.permissions import IsAdminUser
from accounts.pagination import CustomOffsetPagination
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.views import APIView

# Create your views here.

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
    
        return Conversation.objects.filter(
            Q(sender=user) | Q(receiver=user),
            type='regular'
        ).annotate(
            latest_chat=Max('chats__created_at') 
        ).order_by('-latest_chat')
    

class ChatViewSet(viewsets.ModelViewSet):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated]
    
    # get the serializer class based on user role and conversation type
    def get_serializer_class(self):
        user = self.request.user
        conversation_id = self.request.query_params.get('conversation')
        
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id)
                if conversation.type == 'support' and user.is_admin:
                    return SupportChatSerializer
            except Conversation.DoesNotExist:
                pass

        return ChatSerializer
        
    def get_queryset(self):
        user = self.request.user
        conversation_id = self.request.query_params.get('conversation')
        
        if not conversation_id:
            raise ValidationError({"conversation": "This query parameter is required."})

        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        if conversation.type == 'support' and user.is_admin:
            Chat.objects.filter(conversation=conversation, is_read=False).exclude(sender=user).update(is_read=True)
            return Chat.objects.filter(conversation=conversation)

        
        if conversation.sender == user or conversation.receiver == user:
            Chat.objects.filter(conversation=conversation, is_read=False).exclude(sender=user).update(is_read=True)
            return Chat.objects.filter(conversation=conversation)

        
        raise PermissionDenied("You do not have permission to view this conversation.")
    
    def create(self, request, *args, **kwargs):
        user = request.user
        conversation_id = request.query_params.get('conversation')
        if not conversation_id:
            return Response({"detail": "Conversation ID is required."}, status=400)
        
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        if conversation.status == 'blocked':
            return Response({"detail": "This conversation is blocked."}, status=403)
        
        if not (
            conversation.sender == user or 
            conversation.receiver == user or 
            (conversation.type == 'support' and user.is_admin)
        ):
            return Response({"detail": "You are not authorized to post in this conversation."}, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        data['conversation'] = conversation_id
        data['sender'] = user.id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)   


class SupportTypeViewSet(viewsets.ModelViewSet):
    queryset = SupportType.objects.all()
    serializer_class = SupportTypeSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        else:
            return [IsAdminUser()]
        

class TicketViewSet(viewsets.ModelViewSet):
    queryset = SupportTicket.objects.all().order_by('-created_at')
    serializer_class = TicketSerializer
    pagination_class = CustomOffsetPagination
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        elif self.action in ['list', 'retrieve', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]


class SupportConversationViewSet(viewsets.ModelViewSet):
    serializer_class = SupportConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = self.request.query_params.get('role')
        
        if user.is_admin:
            # Admin sees all support tickets
            queryset = Conversation.objects.filter(type='support')
            if role and role == 'user':
                queryset = queryset.filter(sender__user_roles__role__id='CUSTOMER')
            elif role and role == 'service_provider':
                queryset = queryset.filter(sender__user_roles__role__id='SERVICE_PROVIDER')
            
            return queryset.annotate(
                latest_chat=Max('chats__created_at') 
            ).order_by('-latest_chat')
    

        # Regular user sees only their own
        return Conversation.objects.filter(type='support').filter(
            Q(sender=user) | Q(receiver=user)
        )
        
class TicketSummary(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        total_tickets = SupportTicket.objects.count()
        open_tickets = SupportTicket.objects.filter(status='open').count()
        pending_tickets = SupportTicket.objects.filter(status='pending').count()
        resolved_tickets = SupportTicket.objects.filter(status='resolved').count()
        escalated_tickets = SupportTicket.objects.filter(status='escalated').count()

        result = {
            'total': total_tickets,
            'opened': open_tickets,
            'pending': pending_tickets,
            'resolved': resolved_tickets,
            'escalated': escalated_tickets
        }

        return Response(result, status=status.HTTP_200_OK)