from rest_framework import serializers
from .models import Product, Allocation, Condition

class ConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condition
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    condition_list = serializers.CharField(write_only=True, required=False, help_text="Comma separated conditions")
    conditions = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'conditions')

    def validate_imei_number(self, value):
        from .utils import validate_imei
        if not validate_imei(value):
            raise serializers.ValidationError("Invalid IMEI number. Luhn checksum failed.")
        return value

    def create(self, validated_data):
        condition_str = validated_data.pop('condition_list', '')
        product = super().create(validated_data)
        if condition_str:
            for name in [c.strip() for c in condition_str.split(',') if c.strip()]:
                condition, _ = Condition.objects.get_or_create(name=name, store=product.store)
                product.conditions.add(condition)
        return product
    
    def update(self, instance, validated_data):
        condition_str = validated_data.pop('condition_list', None)
        product = super().update(instance, validated_data)
        if condition_str is not None:
            product.conditions.clear()
            for name in [c.strip() for c in condition_str.split(',') if c.strip()]:
                condition, _ = Condition.objects.get_or_create(name=name, store=product.store)
                product.conditions.add(condition)
        return product

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

class TacRecordSerializer(serializers.Serializer):
    tac = serializers.CharField()
    brand = serializers.CharField()
    name = serializers.CharField()
    aka = serializers.ListField(child=serializers.CharField())
    contributor = serializers.CharField()
    comment = serializers.CharField()
    gsmarena_1 = serializers.URLField()
    gsmarena_2 = serializers.URLField()

class TacResponseSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_records = serializers.IntegerField()
    results = TacRecordSerializer(many=True)
