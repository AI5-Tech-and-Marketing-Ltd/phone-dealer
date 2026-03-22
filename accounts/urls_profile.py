from django.urls import path
from .views import ProfileView, ChangePasswordView, DeleteAccountView

urlpatterns = [
    path('', ProfileView.as_view(), name='profile-detail'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),
]
