from rest_framework import generics, permissions
from .models import Product
from stores.models import Store
from .serializers import ProductSerializer
from stores.serializers import StoreSerializer
from .filters import ProductFilter

class MarketplaceListView(generics.ListAPIView):
    """Public read-only product list with filtering."""
    queryset = Product.objects.filter(status='Available', store__is_active=True)
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    permission_classes = [permissions.AllowAny]

class MarketplaceStoreListView(generics.ListAPIView):
    """Public store list."""
    queryset = Store.objects.filter(is_active=True)
    serializer_class = StoreSerializer
    permission_classes = [permissions.AllowAny]

class MarketplaceStoreDetailView(generics.RetrieveAPIView):
    """Public store detail."""
    queryset = Store.objects.filter(is_active=True)
    serializer_class = StoreSerializer
    permission_classes = [permissions.AllowAny]

class MarketplaceStoreProductsView(generics.ListAPIView):
    """Products in a specific store."""
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = ProductFilter

    def get_queryset(self):
        store_id = self.kwargs.get('pk')
        return Product.objects.filter(store_id=store_id, status='Available', store__is_active=True)

class MarketplaceProductDetailView(generics.RetrieveAPIView):
    """Public product detail."""
    queryset = Product.objects.filter(status='Available', store__is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
