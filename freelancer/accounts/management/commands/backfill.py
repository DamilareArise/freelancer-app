from django.core.management.base import BaseCommand
from paymentApp.models import Payment

class Command(BaseCommand):
    def handle(self, *args, **options):
        payments = Payment.objects.filter(user__isnull=True, listing__isnull=False)

        updated = 0
        for payment in payments:
            if payment.listing and payment.listing.created_by_id:
                payment.user_id = payment.listing.created_by_id
                payment.save(update_fields=["user"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Updated {updated} payment records with user information."))
