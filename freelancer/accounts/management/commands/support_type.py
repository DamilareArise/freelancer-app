from django.core.management.base import BaseCommand
from supportApp.models import SupportType

class Command(BaseCommand):
    def handle(self, *args, **options):
        support_types = [
            {
                "name": "General Inquiry",
                "description": "For general questions or information requests."
            },
            {
                "name": "Technical Support",
                "description": "For issues related to the functionality of the app."
            },
            {
                "name": "Billing and Payments",
                "description": "For questions regarding billing, payments, or subscriptions."
            },
            {
                "name": "Account Management",
                "description": "For issues related to account settings, profile updates, or account recovery."
            },
            {
                "name": "Feedback and Suggestions",
                "description": "For providing feedback or suggestions to improve the app."
            }
        ]

        for support_type in support_types:
            SupportType.objects.get_or_create(**support_type)
        
        self.stdout.write(self.style.SUCCESS("Support types created successfully."))