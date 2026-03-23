from django.urls import path, include
from rest_framework import routers
from .views import (
    DashboardStatsView, UserManagementViewSet, AdminStoreViewSet,
    AdminSubscriptionViewSet, AdminBillViewSet, AdminProductViewSet,
    AdminAllocationViewSet
)

router = routers.DefaultRouter()
router.register(r'users', UserManagementViewSet, basename='user-management')
router.register(r'stores', AdminStoreViewSet, basename='admin-store')
router.register(r'subscriptions', AdminSubscriptionViewSet, basename='admin-subscription')
router.register(r'bills', AdminBillViewSet, basename='admin-bill')
router.register(r'products', AdminProductViewSet, basename='admin-product')
router.register(r'allocations', AdminAllocationViewSet, basename='admin-allocation')

urlpatterns = [
    path('dashboard/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('', include(router.urls)),
]
