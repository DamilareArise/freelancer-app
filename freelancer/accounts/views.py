from django.shortcuts import render
from rest_framework.views import APIView
from . import serializers as sz
from rest_framework.response import Response
from rest_framework import status
from .tasks import send_email

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

            return Response(
                {
                    'message':'Registration successfull, Kindly Check your mail for OTP', 
                    'user':user_data
                }, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)