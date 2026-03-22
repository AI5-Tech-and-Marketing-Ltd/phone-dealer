from django.db import models
from django.conf import settings
from cloudinary.models import CloudinaryField

class Product(models.Model):
    STATUS_CHOICES = (
        ('Available', 'Available'),
        ('Allocated', 'Allocated'),
        ('Sold', 'Sold'),
    )

    brand = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    imei_number = models.CharField(max_length=20, unique=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Available')
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='products')
    image = CloudinaryField('image', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.brand} {self.model_name} (IMEI: {self.imei_number})"

class Allocation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='allocations')
    allocated_from = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='allocations_given')
    allocated_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='allocations_received')
    customer = models.ForeignKey('sales.Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='allocations')
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='product_allocations')
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Allocated: {self.product.imei_number}"
