from django.contrib import admin
from .models import Product, Allocation

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['brand', 'model_name', 'imei_number', 'status', 'store']
    list_filter = ['brand', 'status', 'store']
    search_fields = ['imei_number', 'model_name']

@admin.register(Allocation)
class AllocationAdmin(admin.ModelAdmin):
    list_display = ['product', 'allocated_from', 'allocated_to', 'timestamp']
    list_filter = ['timestamp']
