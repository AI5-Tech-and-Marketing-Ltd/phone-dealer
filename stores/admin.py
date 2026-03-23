from django.contrib import admin
from .models import Store, Subscription, Bill, Plan

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['title', 'price_per_user', 'billing_cycle', 'is_active']
    list_filter = ['billing_cycle', 'is_active']

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'owner', 'subscription_plan', 'is_active']
    list_filter = ['subscription_plan', 'is_active']
    search_fields = ['name', 'owner__email']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'store', 'plan', 'expiry_date', 'payment_status']
    list_filter = ['plan', 'payment_status']

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['id', 'reference', 'store', 'bill_type', 'amount', 'status']
    list_filter = ['bill_type', 'status']
    search_fields = ['reference']
