from rest_framework import serializers
from inventory.models import Product
from stores.models import Store

class MarketplaceStoreSerializer(serializers.ModelSerializer):
    """Publicly visible store information."""
    class Meta:
        model = Store
        fields = ('id', 'name', 'logo', 'cover_picture', 'is_active', 'created_at')

class MarketplaceProductSerializer(serializers.ModelSerializer):
    """Public product details."""
    store = MarketplaceStoreSerializer(read_only=True)
    conditions = serializers.StringRelatedField(many=True, read_only=True)
    class Meta:
        model = Product
        fields = ('id', 'brand', 'model_name', 'selling_price', 'status', 'availability', 'store', 'image', 'conditions', 'created_at')
