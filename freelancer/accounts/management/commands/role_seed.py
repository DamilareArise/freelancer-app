from django.core.management.base import BaseCommand
from accounts.models import Role

class Command(BaseCommand):
    help = "Seed roles into the database"

    def handle(self, *args, **options):
        roles = [
            {
                "id": "SUPER",
                "label": "Super Admin",
                "description": "Full platform access",
                "is_admin": True
            },
            {
                "id": "CATEGORY",
                "label": "Category Manager",
                "description": "Manages Listing and property category",
                "is_admin": True
            },
            {
                "id": "SUPPORT",
                "label": "Support Admin",
                "description": "Handle Disputes, Reports, Customer Queries",
                "is_admin": True
            },
            {
                "id": "FINANCE",
                "label": "Finance Admin",
                "description": "Manages subscription, payments, revenue analytics",
                "is_admin": True
            },
            {
                "id": "CUSTOMER",
                "label": "Customer",
                "description": "Looking for a service",
                "is_admin": False
            },
            {
                "id": "SERVICE_PROVIDER",
                "label": "Service Provider",
                "description": "Provides services to customers",
                "is_admin": False
            },
        ]

        for role in roles:
            Role.objects.update_or_create(
                id=role["id"],
                defaults={
                    "label": role["label"],
                    "description": role["description"],
                    "is_admin": role["is_admin"]
                }
            )

        self.stdout.write(self.style.SUCCESS("Roles seeded successfully"))