from django.urls import path
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    SignupView, AccountActivateView, ResendActivationView,
    PasswordResetRequestView, PasswordResetConfirmView, LogoutView
)

# Explicitly tag JWT views so they group under 'Auth' in Swagger
DecoratedTokenObtainPairView = extend_schema(tags=['Auth'])(TokenObtainPairView)
DecoratedTokenRefreshView = extend_schema(tags=['Auth'])(TokenRefreshView)

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', DecoratedTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', DecoratedTokenRefreshView.as_view(), name='token_refresh'),
    path('activate/', AccountActivateView.as_view(), name='activate'),
    path('resend-activation/', ResendActivationView.as_view(), name='resend_activation'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
