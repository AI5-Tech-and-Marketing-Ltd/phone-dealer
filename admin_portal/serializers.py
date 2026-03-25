from rest_framework import serializers
from accounts.models import CustomUser
from stores.models import Store

class AssignStoreSerializer(serializers.Serializer):
    store_id = serializers.IntegerField(required=False, allow_null=True)
    role = serializers.ChoiceField(choices=CustomUser.ROLE_CHOICES, required=False)

class ChangeOwnerSerializer(serializers.Serializer):
    new_owner_email = serializers.EmailField()

class AdminUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = CustomUser
        fields = ('email', 'full_name', 'phone_number', 'password', 'role', 'store', 'is_active')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user

class DashboardStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    total_stores = serializers.IntegerField()
    total_products = serializers.IntegerField()
    active_subscriptions = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
