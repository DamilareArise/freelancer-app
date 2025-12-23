from django.urls import path
from . import views as vw

urlpatterns = [
    path('create-payment-intent/', vw.create_payment_intent), 
    path("webhook/stripe/", vw.stripe_webhook, name="stripe-webhook"),
    path("stripe/requery-payment/", vw.requery_payment_intent, name="requery-payment"),
    path("payment-list/", vw.PaymentListView.as_view(), name="payment-list"),
    path("user-payment-list/", vw.UserPaymentListView.as_view(), name="user-payment-list"),
    path("covers-all/", vw.CoverAllSubscriptionsView.as_view(), name="covers-all"),
]