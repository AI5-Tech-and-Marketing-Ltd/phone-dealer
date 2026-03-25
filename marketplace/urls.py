from django.urls import path, include
from rest_framework import routers
from .views import ProductViewSet, StoreViewSet

router = routers.DefaultRouter()
router.register(r'products', ProductViewSet, basename='marketplace-products')
router.register(r'stores', StoreViewSet, basename='marketplace-stores')

urlpatterns = [
    path('', include(router.urls)),
]
