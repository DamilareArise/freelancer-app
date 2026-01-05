from django.core.management.base import BaseCommand
from accounts.models import User, UserRole


class Command(BaseCommand):
    def handle(self, *args, **options):
        # SEED SUPERUSER ACCOUNT
        email = "arisedamilare5@gmail.com"
        first_name = "Damilare"
        last_name = "Arise"
        phone = "+2349036965140"
        roles = ["SUPER"]
        password = "pass123"
        
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "is_verified": True,
            }
        )
        if created:
            user.set_password(password)
            user.save()
            for role_id in roles:
                UserRole.objects.create(user=user, role_id=role_id)
                
            self.stdout.write(self.style.SUCCESS(f"Superuser '{email}' created successfully."))
        else:
            self.stdout.write(self.style.WARNING(f"Superuser '{email}' already exists."))
                
        