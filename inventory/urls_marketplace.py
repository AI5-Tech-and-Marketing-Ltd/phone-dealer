from django.urls import path
from .marketplace_views import (
    MarketplaceListView, MarketplaceStoreListView, MarketplaceStoreDetailView,
    MarketplaceStoreProductsView, MarketplaceProductDetailView
)

urlpatterns = [
    path('products/', MarketplaceListView.as_view(), name='marketplace-list'),
    path('products/<int:pk>/', MarketplaceProductDetailView.as_view(), name='product-detail'),
    path('stores/', MarketplaceStoreListView.as_view(), name='store-list'),
    path('stores/<int:pk>/', MarketplaceStoreDetailView.as_view(), name='store-detail'),
    path('stores/<int:pk>/products/', MarketplaceStoreProductsView.as_view(), name='store-products'),
    path('', MarketplaceListView.as_view(), name='marketplace-home'),
]
