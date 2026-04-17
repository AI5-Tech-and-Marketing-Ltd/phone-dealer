from django.urls import path, include
from rest_framework import routers
from .views import (
    PlanViewSet, SubscriptionViewSet, BillViewSet, 
    CreateSubscriptionBillView, PayBillView,
    PaystackCallbackView, PaystackWebhookView,
    PaymentCardViewSet, AutoRenewToggleView, InitiateCardTokenizationView
)

router = routers.DefaultRouter()
router.register(r'plans', PlanViewSet, basename='plan')
router.register(r'bills', BillViewSet, basename='bill')
router.register(r'cards', PaymentCardViewSet, basename='card')

urlpatterns = [
    path('subscribe/', CreateSubscriptionBillView.as_view(), name='subscribe'),
    path('subscriptions/auto-renew/', AutoRenewToggleView.as_view(), name='auto-renew'),
    path('cards/add/', InitiateCardTokenizationView.as_view(), name='add-card'),
    path('bills/<int:pk>/pay/', PayBillView.as_view(), name='pay-bill'),
    path('payments/callback/', PaystackCallbackView.as_view(), name='paystack-callback'),
    path('payments/webhook/', PaystackWebhookView.as_view(), name='paystack-webhook'),
    path('', include(router.urls)),
]
