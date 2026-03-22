from django.db import models
from django.conf import settings
from cloudinary.models import CloudinaryField

class Store(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stores')
    subscription_plan = models.CharField(max_length=50, default='Free')
    staff_limit = models.PositiveIntegerField(default=2)
    logo = CloudinaryField('image', null=True, blank=True)
    cover_image = CloudinaryField('image', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.owner.email})"

class Subscription(models.Model):
    PLAN_CHOICES = (
        ('Free', 'Free'),
        ('Basic', 'Basic'),
        ('Premium', 'Premium'),
    )

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='subscriptions')
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES, default='Free')
    start_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    payment_status = models.CharField(max_length=20, default='Pending')
    max_staff = models.PositiveIntegerField(default=2)
    next_billing_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount_per_staff = models.DecimalField(max_digits=12, decimal_places=2, default=10.00)

    def __str__(self):
        return f"{self.store.name} - {self.plan_type} (Expires: {self.expiry_date})"
    
    @property
    def is_active(self):
        from django.utils import timezone
        return self.expiry_date >= timezone.now().date()

class Bill(models.Model):
    BILL_TYPE_CHOICES = (
        ('NewSubscription', 'NewSubscription'),
        ('Renewal', 'Renewal'),
        ('StaffAddition', 'StaffAddition'),
    )
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
        ('Cancelled', 'Cancelled'),
    )
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='bills')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='bills')
    bill_type = models.CharField(max_length=20, choices=BILL_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    description = models.TextField(blank=True)
    staff_count_change = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Bill {self.reference} - {self.store.name} ({self.status})"
