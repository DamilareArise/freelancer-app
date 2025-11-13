from django.core.management.base import BaseCommand
from adminHandlers.models import Charges

class Command(BaseCommand):
    def handle(self, *args, **options):
        charges_obj = [
            {
                'charge_percent': 0.00,
                'charge_fixed': 0.00,
                'for_key': 'super_ad',
                'for_label': 'Super Ad'
            },
            {
                'charge_percent': 0.00,
                'charge_fixed': 0.00,
                'for_key': 'regular_ad',
                'for_label': 'Regular Ad'
            },
            {
                'base_amount': 80.00,
                'charge_percent': 0.00,
                'charge_fixed': 0.00,
                'for_key': 'all_category',
                'for_label': 'All Category'
            },
        ]
        for charge in charges_obj:
            Charges.objects.get_or_create(**charge)
        self.stdout.write(self.style.SUCCESS("Charges created successfully."))
            