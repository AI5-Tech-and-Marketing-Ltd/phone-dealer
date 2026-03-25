from django.contrib import admin
from .models import Plan, Subscription, Bill

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['title', 'price_per_user', 'billing_cycle', 'is_active']
    list_filter = ['billing_cycle', 'is_active']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'store', 'plan', 'expiry_date', 'payment_status']
    list_filter = ['plan', 'payment_status']

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['id', 'reference', 'store', 'bill_type', 'amount', 'status']
    list_filter = ['bill_type', 'status']
    search_fields = ['reference']
