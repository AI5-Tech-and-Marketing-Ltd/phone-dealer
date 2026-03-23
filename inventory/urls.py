from django.urls import path, include
from rest_framework import routers
from .views import (
    ProductViewSet, AllocationViewSet, ConditionViewSet, 
    TacListView, MarketplaceViewSet
)

router = routers.DefaultRouter()
router.register(r'marketplace', MarketplaceViewSet, basename='marketplace')
router.register(r'conditions', ConditionViewSet, basename='condition')
router.register(r'allocations', AllocationViewSet, basename='allocation')
router.register(r'', ProductViewSet, basename='inventory')

urlpatterns = [
    path('tac-list/', TacListView.as_view(), name='tac-list'),
    path('', include(router.urls)),
]
