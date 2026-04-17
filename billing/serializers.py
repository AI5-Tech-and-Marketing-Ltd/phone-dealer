from rest_framework import serializers
from .models import Plan, Subscription, Bill, PaymentCard

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
        read_only_fields = ('start_date', 'payment_status', 'store')

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
    save_card = serializers.BooleanField(default=False)
    auto_renew = serializers.BooleanField(default=False)

class StoreAddStaffSerializer(serializers.Serializer):
    count = serializers.IntegerField(min_value=1)
    save_card = serializers.BooleanField(default=False)

class ReduceStaffSerializer(serializers.Serializer):
    count = serializers.IntegerField(min_value=1)

class PaymentCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentCard
        fields = ['id', 'card_type', 'last4', 'exp_month', 'exp_year', 'bank', 'is_primary', 'created_at']
        read_only_fields = ['id', 'created_at']

class AutoRenewSerializer(serializers.Serializer):
    auto_renew = serializers.BooleanField()
