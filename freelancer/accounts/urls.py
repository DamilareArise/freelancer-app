from django.urls import path
from . import views as vw

urlpatterns = [
    path('register/', vw.RegistrationView.as_view(), name='register'),
]