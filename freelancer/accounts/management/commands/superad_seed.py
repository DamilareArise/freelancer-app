from django.core.management.base import BaseCommand
from adsApp.models import SuperAdsCategory, AppLocation

class Command(BaseCommand):
    def handle(self, *args, **kwargs) -> str | None:
        
        super_ads_categories = [
            {
                "title": "Homepage Featured Ad",
                "price": 180,
                "tier": "1",
                "features": [
                    "Featured on Homepage",
                    "Highest Visibility",
                    "30-Day Duration"
                ]
            },
            {
                "title": "Top Category Listing",
                "price": 150,
                "tier": "2",
                "features": [
                    "Always at Top of Category",
                    "30-Day Duration",
                    "Priority Display"
                ]
            },
            {
                "title": "Search Highlight Ad",
                "price": 150,
                "tier": "3",
                "features": [
                    "Featured at Top in Search Results",
                    "30-Day Duration",
                    "More Clicks & Views"
                ]
            },
            
        ]
        ad_locations = [
            {
                'id': 'FEATURED_SECTION_IN_HOME_PAGE',
                "name": "Featured section in Home page"
            },
            {
                'id': 'BASE_OF_CATEGORY_PROFILE',
                "name": "Base of Category Profile"
            },
            {
                'id': 'SPONSORED_LIST',
                "name": "Sponsored List"
            },
            {
                'id': 'SUCCESSFUL_PAYMENT_SCREEN',
                "name": "Successful payment screen"
            },
            {
                'id': 'BOTTOM_OF_SEARCH_PAGE',
                "name": "Bottom of Search page"
            },
            {
                'id': 'HOW_TO_POST_A_LISTING_SCREEN',
                "name": "How to post a listing screen"
            },  
        ]
        
        for location in ad_locations:
            AppLocation.objects.create(
                id=location['id'],
                name=location['name']
            )
            
        for category in super_ads_categories:
            SuperAdsCategory.objects.create(
                title=category["title"],
                price=category["price"],
                tier=category["tier"],
                features=category["features"]
            )  
            
        self.stdout.write(self.style.SUCCESS("Successfully seeded database"))