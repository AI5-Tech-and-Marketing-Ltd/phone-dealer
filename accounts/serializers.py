from rest_framework import serializers
from .models import CustomUser
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('email', 'full_name', 'phone_number', 'role', 'profile_picture', 'date_joined', 'is_active')
        read_only_fields = ('date_joined', 'is_active')

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'full_name', 'phone_number', 'password')

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            phone_number=validated_data.get('phone_number', ''),
            role='StoreOwner'
        )
        return user

class AddStaffSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = ('email', 'full_name', 'phone_number', 'password')
    
    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            phone_number=validated_data.get('phone_number', ''),
            role='StoreKeeper',
            is_active=True
        )
        return user

class ProfileSerializer(serializers.ModelSerializer):
    subscription = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('email', 'full_name', 'phone_number', 'profile_picture', 'role', 'is_email_verified', 'subscription')
        read_only_fields = ('email', 'role', 'is_email_verified')

    def get_subscription(self, obj):
        from billing.models import Subscription
        from billing.serializers import SubscriptionSerializer
        store = None
        if obj.role == 'StoreOwner':
            store = obj.stores.first()
        elif obj.role == 'StoreKeeper':
            store = obj.store
        
        if store:
            try:
                sub = store.subscription
                return SubscriptionSerializer(sub).data
            except Subscription.DoesNotExist:
                return None
        return None

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

class AccountActivationSerializer(serializers.Serializer):
    token = serializers.CharField()

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        
        # User profile
        from .serializers import ProfileSerializer
        data['user'] = ProfileSerializer(user).data
        
        # Role
        data['role'] = user.role
        
        # Store & Subscription info (already in ProfileSerializer if we use it, but user asked for them specifically)
        # ProfileSerializer already includes 'subscription' field.
        # Let's add store info.
        from stores.models import Store
        from stores.serializers import StoreSerializer
        
        store = None
        if user.role == 'StoreOwner':
            store = user.stores.first()
        elif user.role == 'StoreKeeper':
            store = user.store
            
        if store:
            data['store'] = StoreSerializer(store).data
        else:
            data['store'] = None
            
        return data
