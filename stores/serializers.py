from rest_framework import serializers
from .models import Store, Subscription, Bill

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = '__all__'
        read_only_fields = ('owner', 'is_active', 'created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'
        read_only_fields = ('start_date', 'payment_status')

class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = '__all__'
        read_only_fields = ('created_at', 'paid_at', 'reference', 'status')

class CreateSubscriptionBillSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    plan_type = serializers.ChoiceField(choices=Subscription.PLAN_CHOICES)

class AddStaffSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    count = serializers.IntegerField(min_value=1)

class ReduceStaffSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    count = serializers.IntegerField(min_value=1)
