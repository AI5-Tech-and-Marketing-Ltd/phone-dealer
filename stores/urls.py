from django.urls import path, include
from rest_framework import routers
from .views import (
    StoreViewSet, SubscriptionViewSet, BillViewSet,
    CreateSubscriptionBillView, AddStaffView, ReduceStaffView, StoreStaffCreateView, PayBillView,
    PaystackCallbackView, PaystackWebhookView
)

router = routers.DefaultRouter()
router.register(r'bills', BillViewSet, basename='bill')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'', StoreViewSet, basename='store')

urlpatterns = [
    path('subscribe/', CreateSubscriptionBillView.as_view(), name='subscribe'),
    path('subscriptions/add-staff/', AddStaffView.as_view(), name='add-staff-slot'),
    path('staff/create/', StoreStaffCreateView.as_view(), name='add-staff-account'),
    path('subscriptions/reduce-staff/', ReduceStaffView.as_view(), name='reduce-staff'),
    path('bills/<int:pk>/pay/', PayBillView.as_view(), name='pay-bill'),
    path('payments/callback/', PaystackCallbackView.as_view(), name='paystack-callback'),
    path('payments/webhook/', PaystackWebhookView.as_view(), name='paystack-webhook'),
    path('', include(router.urls)),
]
