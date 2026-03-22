from django.contrib import admin
from .models import Store, Subscription, Bill

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'owner', 'subscription_plan', 'is_active']
    list_filter = ['subscription_plan', 'is_active']
    search_fields = ['name', 'owner__email']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'store', 'plan_type', 'expiry_date', 'payment_status']
    list_filter = ['plan_type', 'payment_status']

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['id', 'reference', 'store', 'bill_type', 'amount', 'status']
    list_filter = ['bill_type', 'status']
    search_fields = ['reference']
