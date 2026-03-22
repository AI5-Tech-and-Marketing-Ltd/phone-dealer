from rest_framework import serializers
from .models import Product, Allocation
from .utils import validate_imei

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate_imei_number(self, value):
        if not validate_imei(value):
            raise serializers.ValidationError("Invalid IMEI number. Luhn checksum failed.")
        return value

class AllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allocation
        fields = '__all__'
        read_only_fields = ('timestamp',)

class BulkSoldSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    imeis = serializers.ListField(child=serializers.CharField(), required=False)
    
    def validate(self, attrs):
        if not attrs.get('ids') and not attrs.get('imeis'):
             raise serializers.ValidationError("Either 'ids' or 'imeis' must be provided.")
        return attrs
