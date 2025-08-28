from django.urls import path, include
from . import views as vw
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register('customer-role', vw.CustomerRoleViewSet, basename='customer-role')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', vw.RegistrationView.as_view(), name='register'),
    path('verify-otp/', vw.VerifyOtp.as_view(), name='verify-otp'),
    path('get-otp/', vw.GetOTP.as_view(), name='get-otp'),
    path('login/', vw.LoginView.as_view(), name='login'),
    path('logout/', vw.LogoutView.as_view(), name='logout'),
    path('password-reset/', vw.PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset-confirm/', vw.PasswordResetConfirmView.as_view(),name='password-reset-confirm'),
    path('change-password/', vw.ChangePassword.as_view(), name='change-password'),
    path('get-user/', vw.GetUser.as_view(), name='get-user'),
    path('update-user/', vw.UpdateUser.as_view(), name='update-user'),
]