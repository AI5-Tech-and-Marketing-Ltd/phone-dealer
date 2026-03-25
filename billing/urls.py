from django.urls import path, include
from rest_framework import routers
from .views import (
    PlanViewSet, SubscriptionViewSet, BillViewSet, 
    CreateSubscriptionBillView, PayBillView,
    PaystackCallbackView, PaystackWebhookView
)

router = routers.DefaultRouter()
router.register(r'plans', PlanViewSet, basename='plan')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'bills', BillViewSet, basename='bill')

urlpatterns = [
    path('subscribe/', CreateSubscriptionBillView.as_view(), name='subscribe'),
    path('bills/<int:pk>/pay/', PayBillView.as_view(), name='pay-bill'),
    path('payments/callback/', PaystackCallbackView.as_view(), name='paystack-callback'),
    path('payments/webhook/', PaystackWebhookView.as_view(), name='paystack-webhook'),
    path('', include(router.urls)),
]
