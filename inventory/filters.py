from django_filters import rest_framework as filters
from .models import Product

class ProductFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name="selling_price", lookup_expr='gte')
    max_price = filters.NumberFilter(field_name="selling_price", lookup_expr='lte')
    brand = filters.CharFilter(lookup_expr='icontains')
    model = filters.CharFilter(field_name="model_name", lookup_expr='icontains')
    status = filters.CharFilter(lookup_expr='exact')

    class Meta:
        model = Product
        fields = ['brand', 'model', 'status', 'min_price', 'max_price', 'store']
