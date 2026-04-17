import uuid
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework import status, views, generics, permissions
from drf_spectacular.utils import extend_schema, OpenApiTypes, OpenApiExample
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import (
    SignupSerializer, ProfileSerializer, UserSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    AccountActivationSerializer, ChangePasswordSerializer, DeleteAccountSerializer,
    LogoutSerializer, CustomTokenObtainPairSerializer
)
from .models import CustomUser

@extend_schema(tags=['Auth'])
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@extend_schema(
    tags=['Auth'],
    examples=[
        OpenApiExample(
            'Signup Example',
            value={
                'email': 'owner@example.com',
                'full_name': 'Store Owner',
                'phone_number': '08098765432',
                'password': 'ownerpassword123'
            },
            request_only=True
        )
    ]
)
class SignupView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = SignupSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Setup activation
        user.is_active = not settings.PRODUCTION # Set to False until activated in production
        token = str(uuid.uuid4())
        user.activation_token = token
        user.activation_token_created = timezone.now()
        user.save()

        # Send activation email
        activation_url = f"{settings.FRONTEND_URL}/activate?token={token}"
        send_mail(
            'Activate your account',
            f'Please click the link to activate: {activation_url}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        return Response({
            'message': 'Account created. Please check your email to activate.',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

@extend_schema(
    tags=['Auth'], 
    request=AccountActivationSerializer,
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            'Account Activation Example',
            value={'token': 'uuid-activation-token-here'},
            request_only=True
        )
    ]
)
class AccountActivateView(views.APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = AccountActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        try:
            user = CustomUser.objects.get(activation_token=token)
            user.is_active = True
            user.is_email_verified = True
            user.activation_token = None
            user.save()
            return Response({'message': 'Account activated successfully.'})
        except CustomUser.DoesNotExist:
            return Response({'error': 'Invalid activation token.'}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    tags=['Auth'], 
    request=PasswordResetRequestSerializer,
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            'Resend Activation Example',
            value={'email': 'user@example.com'},
            request_only=True
        )
    ]
)
class ResendActivationView(views.APIView):
    """Resend activation email if the user is not active yet."""
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        try:
            user = CustomUser.objects.get(email=email)
            if user.is_active and user.is_email_verified:
                 return Response({'message': 'Account is already active.'}, status=status.HTTP_400_BAD_REQUEST)
            
            token = str(uuid.uuid4())
            user.activation_token = token
            user.activation_token_created = timezone.now()
            user.save()

            activation_url = f"{settings.FRONTEND_URL}/activate?token={token}"
            send_mail(
                'Activate your account',
                f'Please click the link to activate: {activation_url}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            return Response({'message': 'Activation email resent.'})
        except CustomUser.DoesNotExist:
             return Response({'message': 'If an account exists with this email, an activation link has been sent.'})

@extend_schema(
    tags=['Auth'], 
    request=PasswordResetRequestSerializer,
    responses={200: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            'Password Reset Request Example',
            value={'email': 'user@example.com'},
            request_only=True
        )
    ]
)
class PasswordResetRequestView(views.APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        try:
            user = CustomUser.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = f"{settings.FRONTEND_URL}/password-reset/confirm/{uid}/{token}/"
            
            send_mail(
                'Password Reset Request',
                f'Click here to reset your password: {reset_url}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        except CustomUser.DoesNotExist:
            pass 
        
        return Response({'message': 'If an account exists with this email, a reset link has been sent.'})

@extend_schema(
    tags=['Auth'], 
    request=PasswordResetConfirmSerializer,
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            'Password Reset Confirm Example',
            value={
                'uid': 'base64-uid',
                'token': 'reset-token',
                'new_password': 'newsecurepassword123'
            },
            request_only=True
        )
    ]
)
class PasswordResetConfirmView(views.APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['uid']))
            user = CustomUser.objects.get(pk=uid)
            if default_token_generator.check_token(user, serializer.validated_data['token']):
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                return Response({'message': 'Password reset successful.'})
            else:
                return Response({'error': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response({'error': 'Invalid link.'}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    tags=['Auth'], 
    request=LogoutSerializer,
    responses={205: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            'Logout Example',
            value={'refresh': 'token-string-here'},
            request_only=True
        )
    ]
)
class LogoutView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logged out.'}, status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response({'error': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(tags=['Profile'])
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

@extend_schema(
    tags=['Profile'], 
    request=ChangePasswordSerializer,
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            'Change Password Example',
            value={
                'old_password': 'currentpassword123',
                'new_password': 'newsecurepassword123'
            },
            request_only=True
        )
    ]
)
class ChangePasswordView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'error': 'Wrong password.'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'message': 'Password changed.'})

@extend_schema(
    tags=['Profile'], 
    request=DeleteAccountSerializer,
    responses={204: None, 400: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            'Delete Account Example',
            value={'password': 'currentpassword123'},
            request_only=True
        )
    ]
)
class DeleteAccountView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = DeleteAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['password']):
            return Response({'error': 'Wrong password.'}, status=status.HTTP_400_BAD_REQUEST)
        user.delete()
        return Response({'message': 'Account deleted.'}, status=status.HTTP_204_NO_CONTENT)
