from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from .models import Payment
import json, uuid
import stripe
from django.conf import settings
from django.utils import timezone
from adsApp.models import Ad
from adminHandlers.models import CategoryPricing, Charges
from django.shortcuts import get_object_or_404
from listing.models import Listing
from adsApp.models import SuperAdsCategory
from dateutil.relativedelta import relativedelta
from django.views.decorators.http import require_POST
from rest_framework import generics
from accounts.permission import IsAdminUser
from .serializers import PaymentSerializer, PaymentSerializerForSuperAd, PaymentSerializerForEarnings
from accounts.pagination import CustomOffsetPagination
from django.db.models import Q, OuterRef, Subquery, Prefetch
from django.utils.timezone import make_aware, get_current_timezone
from datetime import datetime
from rest_framework.permissions import IsAuthenticated
from accounts.utils import send_email
from decimal import Decimal
 

stripe.api_key = settings.STRIPE_SECRET_KEY

def successful_payment(transaction_id=None):
    payment = Payment.objects.filter(transaction_id=transaction_id).first()
    if not payment or payment.status == "completed":
        return   
    
    elif payment.booking:
        payment.status = "completed"
        payment.mode = "booking"
        payment.save()
        
        context = {
            "subject": "Booking payment successful",
            "user": payment.booking.requester,
            "payment": payment,
            "booking": payment.booking
        }

    try:
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
                "user": payment.listing.created_by,
                "payment":payment,
                "ad": ad,
                "duration": ad_duration
            }
            template = None
            if payment.super_ad.tier == 1:
                template = 'super-ad-tier1-payment.html'
            elif payment.super_ad.tier == 2:
                template = 'super-ad-tier2-payment.html'
            elif payment.super_ad.tier == 3:
                template = 'super-ad-tier3-payment.html'
            
            send_email(context, template)
            
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
                "user": payment.listing.created_by,
                "payment":payment,
                "ad": ad,
                "duration": ad_duration
            }
            
            send_email(context, 'regular-ad-payment.html')
            
    except Exception as e:
        print(f"Stripe retrieval failed: {e}")

@csrf_exempt
def create_payment_intent(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            price_id = data.get("price_id") 
            listing_id = data.get("listing_id")
            super_ad_id = data.get("super_ad_id")
            super_ad_month = data.get("super_ad_month")  
            listing = get_object_or_404(Listing, id=listing_id)
            
            categoryPricing = None
            super_ad = None
            charges = None
            if price_id and not super_ad_id:
                categoryPricing = get_object_or_404(CategoryPricing, id=price_id)
                charges = Charges.objects.filter(for_key='regular_ad').first()
                
                net_amount = Decimal(str(categoryPricing.price))
                if not charges:
                    return JsonResponse({"error": "Charges for regular ad not found"}, status=404)
                charge_percent = Decimal(str(charges.charge_percent))
                charge_fixed = Decimal(str(charges.charge_fixed))
                # calculate discount if applicable
                if categoryPricing.discount:
                    discount = (net_amount * Decimal(str(categoryPricing.discount))) / Decimal('100')
                    net_amount = net_amount - discount
                total_amount = net_amount + (net_amount * charge_percent / Decimal('100')) + charge_fixed

            if super_ad_id:
                super_ad = get_object_or_404(SuperAdsCategory, id=super_ad_id)
                if not super_ad_month:
                    return JsonResponse({"error": "super_ad_month is required for super ads"}, status=400)
                charges = Charges.objects.filter(for_key='super_ad').first()
                if not charges:
                    return JsonResponse({"error": "Charges for super ads not found"}, status=404)
                charge_percent = Decimal(str(charges.charge_percent))
                charge_fixed = Decimal(str(charges.charge_fixed))
                net_amount = Decimal(str(super_ad.price)) * Decimal(str(super_ad_month))
                total_amount = net_amount + (net_amount * charge_percent / Decimal('100')) + charge_fixed

            stripe_amount = int(total_amount * Decimal('100'))

            if stripe_amount == 0:
                transaction_id=f"free_listing_{uuid.uuid4().hex}"
                Payment.objects.create(
                    listing=listing,
                    price=categoryPricing,
                    transaction_id=transaction_id,
                    amount_paid=0,
                    net_amount=0,
                    status="completed",
                )
                Ad.objects.create(
                    listing=listing,
                    type='regular_ads',
                    start_date=timezone.now(),
                    end_date=timezone.now() + relativedelta(months=categoryPricing.duration),
                    status='active'
                )
                
                return JsonResponse({"message": "Enjoy Free Listing"}, status=200)
            
            # Step 1: Create the PaymentIntent on Stripe
            intent = stripe.PaymentIntent.create(
                amount=stripe_amount,
                currency="eur",
                payment_method_types=["card"],
            )

            # Step 2: Save a Payment entry to your database
            Payment.objects.create(
                listing=listing,
                price=categoryPricing,
                transaction_id=intent.id,
                super_ad=super_ad,
                super_ad_month=super_ad_month,
                amount_paid=total_amount,
                net_amount=net_amount,
                mode = 'ads',
                status="pending",
            )

            return JsonResponse({"client_secret": intent.client_secret})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)

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
            print(f"Error updating payment status or creating ad: {e}")
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
        
    
    # For Refund
    if event['type'] in ('refund.created', 'refund.updated'):
        refund = event['data']['object']
        charge_id = refund['charge']
        status = refund['status']
        refund_id = refund['id']
        refund_amount = refund['amount']

        try:
           payment =Payment.objects.get(charge_id=charge_id)
           payment.refund_status = status
           payment.refund_id = refund_id
           payment.refund_amount = refund_amount
           payment.save()
        except Payment.DoesNotExist:
            pass  

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
                print(f"Error updating payment status or creating ad: {e}")
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
        elif ad_type == 'earnings':
            return PaymentSerializerForEarnings
        else: 
            return PaymentSerializer
    
    def get_queryset(self):
        params = self.request.query_params
        ad_type = params.get('ad_type', 'regular_ads')
        ad_qs = Ad.objects.filter(type=ad_type).order_by('-end_date')
        
        queryset = Payment.objects.select_related('listing__property', 'listing__category') \
            .prefetch_related(Prefetch('listing__ads', queryset=ad_qs)) 
            
        # Only show super_ad payments if that's the ad_type selected
        if ad_type == 'super_ads':
            queryset = queryset.filter(super_ad__isnull=False)
        elif ad_type == 'earnings':
            queryset = queryset.filter(mode = 'booking')
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
    

# paymentList for user endpoint
class UserPaymentListView(generics.ListAPIView):
    pagination_class = CustomOffsetPagination
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        ad_type = self.request.query_params.get('ad_type', 'regular_ads')
        if ad_type == 'super_ads':
            return PaymentSerializerForSuperAd
        elif ad_type == 'earnings':
            return PaymentSerializerForEarnings
        else: 
            return PaymentSerializer

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params
        ad_type = params.get('ad_type', 'regular_ads')
        ad_qs = Ad.objects.filter(type=ad_type).order_by('-end_date')
        
        if ad_type == 'earnings':
            queryset = Payment.objects.filter(booking__requester = user)
        else:   
            queryset = Payment.objects.filter(listing__created_by=user).select_related('listing__property', 'listing__category').prefetch_related(Prefetch('listing__ads', queryset=ad_qs))
        
        # Only show super_ad payments if that's the ad_type selected
        if ad_type == 'super_ads':
            queryset = queryset.filter(super_ad__isnull=False)
        elif ad_type == 'earnings':
            queryset = queryset.filter(mode = 'booking')
        else:
            queryset = queryset.filter(price__isnull=False)
            
        # Filter by status if provided
        status = params.get('status')
        if status:
            status = status.split(',')
            queryset = queryset.filter(status__in=status)

        return queryset.order_by('-created_at','-updated_at')