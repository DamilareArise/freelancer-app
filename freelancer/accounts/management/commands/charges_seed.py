from django.core.management.base import BaseCommand
from adminHandlers.models import Charges

class Command(BaseCommand):
    def handle(self, *args, **options):

        charges_obj = [
            {
                'charge_percent': 2.9,
                'charge_fixed': 0.30,
                'for_key': 'super_ad',
                'for_label': 'Super Ad'
            },
            {
                'charge_percent': 2.9,
                'charge_fixed': 0.30,
                'for_key': 'regular_ad',
                'for_label': 'Regular Ad'
            },
            {
                'base_amount': 80.00,
                'charge_percent': 2.9,
                'charge_fixed': 0.30,
                'for_key': 'all_category',
                'for_label': 'All Category'
            },
        ]
        for charge in charges_obj:
            obj, created = Charges.objects.get_or_create(
                for_key=charge['for_key'],
                defaults=charge
            )
            if not created:
                for key, value in charge.items():
                    setattr(obj, key, value)
                obj.save()
                
        self.stdout.write(self.style.SUCCESS("Charges created successfully."))
            