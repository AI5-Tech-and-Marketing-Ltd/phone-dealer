from django.contrib import admin
from .models import Sale, Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'phone', 'store']
    search_fields = ['full_name', 'phone']

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'sold_by', 'customer_name', 'sale_price', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['product__imei_number', 'customer_name']
