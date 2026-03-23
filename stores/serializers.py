from rest_framework import serializers
from .models import Store, Subscription, Bill, Plan

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = '__all__'

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = '__all__'
        read_only_fields = ('owner', 'is_active', 'created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)

class SubscriptionSerializer(serializers.ModelSerializer):
    plan_details = PlanSerializer(source='plan', read_only=True)
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
    plan_id = serializers.IntegerField()
    staff_count = serializers.IntegerField(min_value=1, default=2)

class AddStaffSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    count = serializers.IntegerField(min_value=1)

class ReduceStaffSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    count = serializers.IntegerField(min_value=1)
