from rest_framework import serializers
from .models import Plan, Subscription, Bill

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = '__all__'

class SubscriptionSerializer(serializers.ModelSerializer):
    plan_details = PlanSerializer(source='plan', read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = '__all__'
        read_only_fields = ('start_date', 'payment_status')

class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = '__all__'
        read_only_fields = ('created_at', 'paid_at', 'reference', 'status')

class BillCheckoutResponseSerializer(serializers.Serializer):
    checkout_url = serializers.URLField()
    reference = serializers.CharField()
    amount = serializers.FloatField()
    access_code = serializers.CharField(required=False)

class CreateSubscriptionBillSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    staff_count = serializers.IntegerField(min_value=1, default=2)

class StoreAddStaffSerializer(serializers.Serializer):
    count = serializers.IntegerField(min_value=1)

class ReduceStaffSerializer(serializers.Serializer):
    count = serializers.IntegerField(min_value=1)
