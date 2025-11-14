from django.core.management.base import BaseCommand
from adminHandlers.models import Charges
from paymentApp.models import Payment
from dateutil.relativedelta import relativedelta

class Command(BaseCommand):
    def handle(self, *args, **options):
        
        payments = Payment.objects.filter(
            covers_all=True,
            covers_all_month__isnull=False,
            status='completed'
        )

        for p in payments:
            if p.created_at:  # should always be true
                p.due_date = p.created_at + relativedelta(months=p.covers_all_month)
                p.save()
        self.stdout.write(self.style.SUCCESS("Payment due dates updated successfully."))
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
            