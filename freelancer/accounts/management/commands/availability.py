from django.core.management.base import BaseCommand
from accounts.utils import create_default_availability

class Command(BaseCommand):
    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(roles__id='SERVICE_PROVIDER')

        for user in users:
            create_default_availability(user)

        self.stdout.write(self.style.SUCCESS("Default availability created for SERVICE_PROVIDER users."))