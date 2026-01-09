from django.core.management.base import BaseCommand
from supportApp.models import SupportType


class Command(BaseCommand):
    help = "Seed initial support types"

    def handle(self, *args, **options):
        support_types = [
            {
                "name_en": "General Inquiry",
                "name_hr": "Opći upit",
                "description_en": "For general questions or information requests.",
                "description_hr": "Za opća pitanja ili zahtjeve za informacijama."
            },
            {
                "name_en": "Technical Support",
                "name_hr": "Tehnička podrška",
                "description_en": "For issues related to the functionality of the app.",
                "description_hr": "Za probleme vezane uz funkcionalnost aplikacije."
            },
            {
                "name_en": "Billing and Payments",
                "name_hr": "Naplata i plaćanja",
                "description_en": "For questions regarding billing, payments, or subscriptions.",
                "description_hr": "Za pitanja vezana uz naplatu, plaćanja ili pretplate."
            },
            {
                "name_en": "Account Management",
                "name_hr": "Upravljanje računom",
                "description_en": "For issues related to account settings, profile updates, or account recovery.",
                "description_hr": "Za probleme vezane uz postavke računa, ažuriranje profila ili oporavak računa."
            },
            {
                "name_en": "Feedback and Suggestions",
                "name_hr": "Povratne informacije i prijedlozi",
                "description_en": "For providing feedback or suggestions to improve the app.",
                "description_hr": "Za slanje povratnih informacija ili prijedloga za poboljšanje aplikacije."
            }
        ]

        for support_type in support_types:
            SupportType.objects.get_or_create(
                name_en=support_type["name_en"],
                defaults=support_type
            )

        self.stdout.write(
            self.style.SUCCESS("✅ Support types created successfully.")
        )
