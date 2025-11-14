from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views as vw

router = DefaultRouter()
router.register(r'conversations', vw.ConversationViewSet, basename='conversation')
router.register(r'chats', vw.ChatViewSet, basename='chat')
router.register(r'support-ticket', vw.TicketViewSet, basename='support-ticket')
router.register(r'support-type', vw.SupportTypeViewSet, basename='support-type')
router.register(r'support-conversation', vw.SupportConversationViewSet, basename='support-conversation')
urlpatterns = [
    path('', include(router.urls)),
    path('ticket-summary/', vw.TicketSummary.as_view(), name='ticket-summary'),
]