from django.db import models
from django.conf import settings
from cloudinary.models import CloudinaryField

class Plan(models.Model):
    CYCLE_CHOICES = (
        ('Monthly', 'Monthly'),
        ('Yearly', 'Yearly'),
    )

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price_per_user = models.DecimalField(max_digits=12, decimal_places=2, help_text="Price per staff slot")
    features = models.JSONField(default=list, help_text="List of feature names")
    billing_cycle = models.CharField(max_length=20, choices=CYCLE_CHOICES, default='Monthly')
    renewal_period_days = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} ({self.billing_cycle})"

class Store(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stores')
    subscription_plan = models.CharField(max_length=50, default='Free')
    staff_limit = models.PositiveIntegerField(default=2)
    logo = CloudinaryField('image', null=True, blank=True)
    cover_picture = CloudinaryField('image', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.owner.email})"

class Subscription(models.Model):
    store = models.OneToOneField(Store, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name='active_subscriptions')
    plan_type_legacy = models.CharField(max_length=20, default='Free') # For backward compat
    start_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    payment_status = models.CharField(max_length=20, default='Pending')
    max_staff = models.PositiveIntegerField(default=2)
    next_billing_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"{self.store.name} - {self.plan.title if self.plan else self.plan_type_legacy} (Expires: {self.expiry_date})"
    
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
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name='bills')
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
