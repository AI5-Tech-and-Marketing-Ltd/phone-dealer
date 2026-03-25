from rest_framework import viewsets, permissions
from django_filters import rest_framework as filters
from inventory.models import Product
from stores.models import Store
from .serializers import MarketplaceProductSerializer, MarketplaceStoreSerializer

class ProductFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name="selling_price", lookup_expr='gte')
    max_price = filters.NumberFilter(field_name="selling_price", lookup_expr='lte')
    brand = filters.CharFilter(lookup_expr='icontains')
    model = filters.CharFilter(field_name="model_name", lookup_expr='icontains')
    class Meta:
        model = Product
        fields = ['brand', 'model', 'min_price', 'max_price', 'store']

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = MarketplaceProductSerializer
    filterset_class = ProductFilter
    search_fields = ['imei_number', 'brand', 'model_name']
    ordering_fields = ['selling_price', 'created_at']
    def get_queryset(self):
        return Product.objects.filter(status='Available', availability='Public').select_related('store').prefetch_related('conditions')

class StoreViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = MarketplaceStoreSerializer
    def get_queryset(self):
        return Store.objects.filter(is_active=True, products__availability='Public', products__status='Available').distinct()
