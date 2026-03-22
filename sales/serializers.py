from rest_framework import serializers
from .models import Sale, Customer
from inventory.models import Product

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'
        read_only_fields = ('store', 'created_at')

    def create(self, validated_data):
        # We'll need to set the store in the view or here if store is provided
        return super().create(validated_data)

class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = ('sold_by', 'timestamp')

    def validate_product(self, value):
        if value.status != 'Available':
            raise serializers.ValidationError(f"Product {value.imei_number} is currently {value.status}")
        return value

    def create(self, validated_data):
        validated_data['sold_by'] = self.context['request'].user
        return super().create(validated_data)
