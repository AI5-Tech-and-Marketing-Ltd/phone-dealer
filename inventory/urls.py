from django.urls import path, include
from rest_framework import routers
from .views import ProductViewSet, AllocationViewSet

router = routers.DefaultRouter()
router.register(r'allocations', AllocationViewSet, basename='allocation')
router.register(r'', ProductViewSet, basename='inventory')

urlpatterns = [
    path('', include(router.urls)),
]
