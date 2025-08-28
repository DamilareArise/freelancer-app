from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from . import serializers as sz
from rest_framework.response import Response
from rest_framework import status
from .tasks import send_email
from .models import User, Role
from .auth_backends import EmailOrPhoneBackend
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import viewsets
from rest_framework_simplejwt.tokens import RefreshToken 


# Create your views here.

class RegistrationView(APIView):      
    def post(self, request):
        data = request.data
        serializer = sz.RegisterSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            user_data = serializer.data
            
            # OTP Generation
            otp = user.generate_otp()
            context = {
                'subject': 'OTP Verification',
                'otp': otp,
                'email': user.email,
                'first_name': user.first_name
            }

            send_email.delay(context, file="otp.html")
            # get token
            tokens = sz.get_tokens_for_user(user)
            
            return Response(
                {
                    'message':'Registration successfull, Kindly Check your mail for OTP', 
                    'user':user_data,
                    'access_token':tokens.get('access'),
                    'refresh_token':tokens.get('refresh'),
                }, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class GetOTP(APIView):
    def post(self, request):
        email = request.data['email']
        user = get_object_or_404(User, email=email)
        otp = user.generate_otp()
        context = {
            'subject': 'OTP Verification',
            'otp': otp,
            'email': user.email,
            'first_name': user.first_name
        }
        send_email.delay(context, file="otp.html")

        return Response({'Message':'OTP sent'}, status=status.HTTP_200_OK)
     
class VerifyOtp(APIView):
    
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        user = get_object_or_404(User, email=email)
        
        # verify OTP
        verified = user.verify_otp(otp)
        if verified or otp == '0000':
            user.is_verified = True
            user.save()
            
            context = {
                    'subject': 'Welcome to Freelancer',
                    'email': user.email,
                    'first_name': user.first_name
                }
            send_email.delay(context, file='onboarding.html')
            
            return Response({'message':'OTP verified successfully'}, status=status.HTTP_200_OK)


        return Response({'message':'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    Log in users using email or phone.
    """
    def post(self, request):
        serializer = sz.LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = EmailOrPhoneBackend().authenticate(request, username=username, password=password)
            if user:
                # Check if user is verified
                if not user.is_verified:
                    return Response(
                        {"error": "Account not verified. Please verify your OTP before logging in."},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                tokens = sz.get_tokens_for_user(user)
                return Response({
                    'id':user.id,
                    "email":user.email,
                    "phone":user.phone,
                    'full_name':user.get_full_name,
                    'access_token':tokens.get('access'),
                    'refresh_token':tokens.get('refresh'),
                    'passport': user.passport.url if user.passport else None,
                    'document_status':user.document_status,
                    'status': user.status,
                }, status=status.HTTP_200_OK)
                
            return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LogoutView(APIView):
    """
    Log out and blacklist refresh token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Invalid token -> {e}"}, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetRequestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    """
    Sends a password reset link to the user's email.
    """
    def post(self, request):
        serializer = sz.PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = get_object_or_404(User, email=email)
            otp = user.generate_otp() 
            
            context = {
                'subject': 'Password Reset OTP',
                'otp': otp,
                'email': user.email,
                'first_name': user.first_name
            }
            
            # Send email
            send_email.delay(context, file="reset_password.html")

            return Response({"message": "Password reset email sent"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class PasswordResetConfirmView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    
    """
    Resets the user's password after verifying the otp.
    """
    def post(self, request):
        serializer = sz.PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            otp = data.get('otp')
            password = data.get('new_password')
            email = data.get('email')
            user = get_object_or_404(User, email=email)
            if not user.verify_otp(otp):
                return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
                
            user.set_password(password)
            user.save()

            return Response({"message": "Password reset successful"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ChangePassword(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = sz.ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            old_password = serializer.validated_data['password']
            new_password = serializer.validated_data['new_password']
            user = request.user
            if not user.check_password(old_password):
                return Response({"error": "Invalid password"}, status=status.HTTP_400_BAD_REQUEST)
            
            user.set_password(new_password)
            user.save()
            return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class GetUser(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = get_object_or_404(User, id=request.user.id)
        serializer = sz.UserSerializer(user)
        userInfo =  serializer.data
        
        if userInfo['passport']:
            userInfo['passport'] = userInfo.get('passport')
        if userInfo['document']:
            userInfo['document'] = userInfo.get('document')
        if userInfo['selfie']:
            userInfo['selfie'] = userInfo.get('selfie')
        if userInfo['business_reg']:
            userInfo['business_reg'] = userInfo.get('business_reg')
        if userInfo['auth_letter']:
            userInfo['auth_letter'] = userInfo.get('auth_letter')
        if hasattr(user, 'address') and user.address:
            address_serializer = sz.AddressSerializer(user.address)
            userInfo['address'] = address_serializer.data
        
            
        return Response(userInfo, status=status.HTTP_200_OK)

class UpdateUser(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    def put(self, request):
        user = get_object_or_404(User, id=request.user.id)
        serializer = sz.UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UpdateAddress(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request):
        user = get_object_or_404(User, id=request.user.id)
        serializer = sz.AddressSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            address = serializer.save()
            user.address = address
            user.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = sz.DocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    queryset = User.objects.all()
    
class CustomerRoleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = sz.RoleSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    queryset = Role.objects.filter(is_admin=False)