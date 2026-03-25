from rest_framework import serializers
from .models import Store
from billing.serializers import SubscriptionSerializer

class StoreSerializer(serializers.ModelSerializer):
    subscription = SubscriptionSerializer(read_only=True)
    class Meta:
        model = Store
        fields = '__all__'
        read_only_fields = ('owner', 'is_active', 'created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)

class StorePublicSerializer(serializers.ModelSerializer):
    """Publicly visible store information."""
    class Meta:
        model = Store
        fields = ('id', 'name', 'logo', 'cover_picture', 'is_active', 'created_at')
        read_only_fields = ('is_active', 'created_at')
