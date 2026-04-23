from django.db import models
from django.conf import settings

class Condition(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='conditions')

    class Meta:
        unique_together = ('name', 'store')

    def __str__(self):
        return self.name

class Product(models.Model):
    STATUS_CHOICES = (
        ('Available', 'Available'),
        ('Allocated', 'Allocated'),
        ('Sold', 'Sold'),
    )
    AVAILABILITY_CHOICES = (
        ('Private', 'Private'),
        ('Public', 'Public'),
    )

    brand = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    imei_number = models.CharField(max_length=20, unique=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Available')
    availability = models.CharField(max_length=10, choices=AVAILABILITY_CHOICES, default='Private')
    
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='products')
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    conditions = models.ManyToManyField(Condition, blank=True, related_name='products')
    sold_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.brand} {self.model_name} (IMEI: {self.imei_number})"

class Allocation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='allocations')
    allocated_from = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='allocations_given')
    allocated_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='allocations_received')
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='product_allocations')
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Allocated: {self.product.imei_number}"

class TacRecord(models.Model):
    tac         = models.CharField(max_length=8, unique=True, db_index=True)
    brand       = models.CharField(max_length=100, blank=True, default='')
    name        = models.CharField(max_length=200, blank=True, default='')
    aka         = models.JSONField(default=list, blank=True)   # stored as JSON array
    contributor = models.CharField(max_length=200, blank=True, default='')
    comment     = models.TextField(blank=True, default='')
    gsmarena_1  = models.URLField(blank=True, default='')
    gsmarena_2  = models.URLField(blank=True, default='')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['tac']

    def __str__(self):
        return f"{self.tac} — {self.brand} {self.name}"

