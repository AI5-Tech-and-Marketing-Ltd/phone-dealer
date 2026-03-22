from rest_framework import serializers
from .models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('email', 'full_name', 'role', 'profile_picture', 'date_joined', 'is_active')
        read_only_fields = ('date_joined', 'is_active')

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'full_name', 'password')

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            role='StoreOwner' # Default for public signup
        )
        return user

class AddStaffSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = ('email', 'full_name', 'password')
    
    def create(self, validated_data):
        # View will handle setting the role to StoreKeeper 
        # and checking owner permissions
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            role='StoreKeeper',
            is_active=True # Staff added by owner can be active immediately or wait for email
        )
        return user

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('email', 'full_name', 'profile_picture', 'role', 'is_email_verified')
        read_only_fields = ('email', 'role', 'is_email_verified')

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
