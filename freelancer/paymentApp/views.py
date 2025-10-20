from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from listing.models import Listing
from paymentApp.models import Payment
import json

# Create your views here.
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
            
            
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)