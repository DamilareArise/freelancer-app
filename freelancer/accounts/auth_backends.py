from django.contrib.auth.backends import ModelBackend
from .models import User


class EmailOrPhoneBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in with either email or phone.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        user = None
        if username:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(phone=username)
                except User.DoesNotExist:
                    return None
        
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
        