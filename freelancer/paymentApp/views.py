from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from listing.models import Listing
from paymentApp.models import Payment
import json, stripe, logging
from adminHandlers.models import CategoryPricing, Charges
from django.conf import settings
from decimal import Decimal
from adsApp.models import SuperAdsCategory, Ad
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from accounts.tasks import send_email
from django.db import transaction
from django.views.decorators.http import require_POST
from rest_framework import generics
from accounts.permissions import IsAdminUser
from accounts.pagination import CustomOffsetPagination
from django.db.models import Prefetch, Q, OuterRef, Subquery 
from datetime import datetime
from django.utils.timezone import make_aware, get_current_timezone
from .serializers import PaymentSerializer, PaymentSerializerForSuperAd
from rest_framework.permissions import IsAuthenticated


logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


def successful_payment(transaction_id=None):
    payment = Payment.objects.filter(transaction_id=transaction_id).first()
    if not payment or payment.status == "completed":
        return   
        
    try:
        with transaction.atomic():
            
            payment.status = "completed"
            payment.save()
            ad = None
            if payment.super_ad:
                ad = Ad.objects.create(
                    listing= payment.listing,
                    super_ads_category=payment.super_ad,
                    type = 'super_ads',
                    status = 'active',
                    start_date=timezone.now(),
                    end_date=timezone.now() + relativedelta(months=int(payment.super_ad_month))
                )
                
                ad_duration = (ad.end_date - ad.start_date).days
                context = {
                    "subject": "Superad payment successful",
                    "user": payment.listing.created_by.id,
                    "payment":payment.id,
                    "ad": ad.id,
                    "duration": ad_duration
                }
                
                template = None
                if payment.super_ad.tier == 1:
                    template = 'super-ad-tier1-payment.html'
                elif payment.super_ad.tier == 2:
                    template = 'super-ad-tier2-payment.html'
                elif payment.super_ad.tier == 3:
                    template = 'super-ad-tier3-payment.html'
                    
                send_email.delay(context, template)
        
            else:
                ad = Ad.objects.create(
                    listing=payment.listing,
                    type='regular_ads',
                    start_date=timezone.now(),
                    end_date=timezone.now() + relativedelta(months=payment.price.duration),
                    status='active'
                )
                ad_duration = (ad.end_date - ad.start_date).days
                context = {
                    "subject": "Regular ad payment successful",
                    "user": payment.listing.created_by.id,
                    "payment":payment.id,
                    "ad": ad.id,
                    "duration": ad_duration
                }
                
                send_email.delay(context, 'regular-ad-payment.html')    
            
    except Exception as e:
        logger.exception(f"Payment processing failed for transaction {transaction_id}: {e}") 

# Create your views here.
@csrf_exempt
def create_payment_intent(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        price_id = data.get("price_id")
        listing_id = data.get("listing_id")
        super_ad_id = data.get("super_ad_id")
        super_ad_month = data.get("super_ad_month")

        listing = get_object_or_404(Listing, id=listing_id)

        
        categoryPricing = None
        super_ad = None

        # ✅ REGULAR AD
        if price_id and not super_ad_id:
            categoryPricing = get_object_or_404(CategoryPricing, id=price_id)
            charges = Charges.objects.filter(for_key='regular_ad').first()

            if not charges:
                return JsonResponse({"error": "Charges for regular ad not found"}, status=404)

            net_amount = categoryPricing.price
            if categoryPricing.discount:
                net_amount -= categoryPricing.discount

            charge_percent = charges.charge_percent or Decimal('0.0')
            charge_fixed = charges.charge_fixed or Decimal('0.0')

            price_charges = (net_amount * charge_percent / Decimal('100.0')) + charge_fixed
            total_amount = net_amount + price_charges

        # ✅ SUPER AD
        elif super_ad_id:
            super_ad = get_object_or_404(SuperAdsCategory, id=super_ad_id)

            if not super_ad_month:
                return JsonResponse({"error": "super_ad_month is required for super ads"}, status=400)

            charges = Charges.objects.filter(for_key='super_ad').first()
            if not charges:
                return JsonResponse({"error": "Charges for super ads not found"}, status=404)

            charge_percent = charges.charge_percent or Decimal('0.0')
            charge_fixed = charges.charge_fixed or Decimal('0.0')

            net_amount = super_ad.price * Decimal(str(super_ad_month))
            price_charges = (net_amount * charge_percent / Decimal('100.0')) + charge_fixed
            total_amount = net_amount + price_charges

        else:
            return JsonResponse({"error": "Either price_id or super_ad_id is required"}, status=400)

        # ✅ Stripe amount in cents (int)
        stripe_amount = int(total_amount * 100)

        intent = stripe.PaymentIntent.create(
            amount=stripe_amount,
            currency="eur",
            payment_method_types=["card"],
        )

        # ✅ Save Payment
        Payment.objects.create(
            listing=listing,
            price=categoryPricing,
            transaction_id=intent.id,
            super_ad=super_ad,
            super_ad_month=super_ad_month,
            amount_paid=total_amount,
            net_amount=net_amount,
            status="pending",
        )

        return JsonResponse({"client_secret": intent.client_secret})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    # Step 1: Successful payment
    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        transaction_id = intent["id"]
        
        try:
            successful_payment(transaction_id)
        except Exception as e:
            logger.exception(f"Error processing successful payment for transaction {transaction_id}: {e}")
            # send mail to admin
            
            return HttpResponse(status=500)
        
    
    # Step 2: Failed payment
    elif event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        transaction_id = intent["id"]
        print('Failed payment: ', intent)

        Payment.objects.filter(transaction_id=transaction_id).update(status="failed")
    
    elif event['type'] == "payment_intent.canceled":
        intent = event["data"]["object"]
        transaction_id = intent["id"]
        print('Canceled payment: ', intent)
        
        Payment.objects.filter(transaction_id=transaction_id).update(status="canceled")
        
    return HttpResponse(status=200)


@csrf_exempt
@require_POST
def requery_payment_intent(request):
    try:
        data = json.loads(request.body)
        payment_intent_id = data.get("payment_intent_id")

        if not payment_intent_id:
            return JsonResponse({"error": "PaymentIntent ID is required."}, status=400)

        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        status = intent.status
        
        if status == "succeeded":
            try:
               successful_payment(payment_intent_id)
            except Exception as e:
                logger.exception(f"Error processing successful payment for transaction {payment_intent_id}: {e}")
                # send mail to admin
                
                return HttpResponse(status=500) 
            
        elif status == "payment_failed":
            Payment.objects.filter(transaction_id=payment_intent_id).update(status="failed")
        else:
            Payment.objects.filter(transaction_id=payment_intent_id).update(status="canceled")

        return JsonResponse({
            "status": status,
            "amount_received": intent.amount_received,
            "currency": intent.currency,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


class PaymentListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    pagination_class = CustomOffsetPagination
    
    def get_serializer_class(self):
        ad_type = self.request.query_params.get('ad_type', 'regular_ads')
        if ad_type == 'super_ads':
            return PaymentSerializerForSuperAd
        else: 
            return PaymentSerializer
    
    def get_queryset(self):
        params = self.request.query_params
        ad_type = params.get('ad_type', 'regular_ads')
        ad_qs = Ad.objects.filter(type=ad_type).order_by('-end_date')
        
        queryset = Payment.objects.select_related('listing__service', 'listing__category') \
            .prefetch_related(Prefetch('listing__ads', queryset=ad_qs)) 
            
        # Only show super_ad payments if that's the ad_type selected
        if ad_type == 'super_ads':
            queryset = queryset.filter(super_ad__isnull=False)
        else:
            queryset = queryset.filter(price__isnull=False)
                
        # Filter by status if provided
        status = params.get('status')
        search = params.get('search')
        date_range = params.get('date_range')

        if search:
            queryset = queryset.filter(
                Q(listing__property__header__icontains=search) |
                Q(listing__category__name__icontains=search) |
                Q(transaction_id__icontains=search)
            )
        if status:
            status = status.split(',')
            queryset = queryset.filter(status__in=status)
        
        queryset = queryset.order_by('-created_at','-updated_at')
        
        if date_range:
            start_date_str, end_date_str = [d.strip() for d in date_range.split(',')]
            tz = get_current_timezone()
            start_date = make_aware(datetime.strptime(start_date_str, "%Y-%m-%d"), timezone=tz)
            end_date = make_aware(datetime.strptime(end_date_str, "%Y-%m-%d"), timezone=tz)

            ad_filter = Ad.objects.filter(
                listing=OuterRef('listing_id'),
                type=ad_type,
                end_date__range=(start_date, end_date)
            ).order_by('-end_date')

            queryset = queryset.annotate(
                latest_ad_end_date=Subquery(ad_filter.values('end_date')[:1])
            ).filter(latest_ad_end_date__isnull=False)

        return queryset 
    
    
class UserPaymentListView(generics.ListAPIView):
    pagination_class = CustomOffsetPagination
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        ad_type = self.request.query_params.get('ad_type', 'regular_ads')
        if ad_type == 'super_ads':
            return PaymentSerializerForSuperAd
        else: 
            return PaymentSerializer

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params
        ad_type = params.get('ad_type', 'regular_ads')
        ad_qs = Ad.objects.filter(type=ad_type).order_by('-end_date')
        
        queryset = Payment.objects.filter(listing__created_by=user).select_related('listing__service', 'listing__category').prefetch_related(Prefetch('listing__ads', queryset=ad_qs))
        
        # Only show super_ad payments if that's the ad_type selected
        if ad_type == 'super_ads':
            queryset = queryset.filter(super_ad__isnull=False)
        else:
            queryset = queryset.filter(price__isnull=False)
            
        # Filter by status if provided
        status = params.get('status')
        if status:
            status = status.split(',')
            queryset = queryset.filter(status__in=status)

        return queryset.order_by('-created_at','-updated_at')