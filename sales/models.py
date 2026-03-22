from django.db import models
from django.conf import settings

class Customer(models.Model):
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='customers')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.phone})"

class Sale(models.Model):
    product = models.OneToOneField('inventory.Product', on_delete=models.CASCADE, related_name='sale')
    sold_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sales')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases')
    customer_name = models.CharField(max_length=255) # Legacy/Fallback
    customer_contact = models.CharField(max_length=20) # Legacy/Fallback
    sale_price = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale: {self.product.imei_number} by {self.sold_by.email}"

    def save(self, *args, **kwargs):
        # Sync with customer object if set
        if self.customer:
            self.customer_name = self.customer.full_name
            self.customer_contact = self.customer.phone
        # Mark product as sold when sale is created
        self.product.status = 'Sold'
        self.product.save()
        super().save(*args, **kwargs)
