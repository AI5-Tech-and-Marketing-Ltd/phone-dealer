from django.db import models
from django.conf import settings
from stores.models import Store

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

class Subscription(models.Model):
    store = models.OneToOneField(Store, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name='active_subscriptions')
    start_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    payment_status = models.CharField(max_length=20, default='Pending')
    max_staff = models.PositiveIntegerField(default=2)
    reduced_slots_balance = models.PositiveIntegerField(default=0)
    next_billing_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    auto_renew = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.store.name} - {self.plan.title if self.plan else 'No Plan'} (Expires: {self.expiry_date})"
    
    @property
    def is_active(self):
        from django.utils import timezone
        return self.expiry_date >= timezone.now().date()

class Bill(models.Model):
    BILL_TYPE_CHOICES = (
        ('NewSubscription', 'NewSubscription'),
        ('Renewal', 'Renewal'),
        ('StaffAddition', 'StaffAddition'),
        ('CardTokenization', 'CardTokenization'),
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
    save_card = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Bill {self.reference} - {self.store.name} ({self.status})"

class PaymentCard(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='payment_cards')
    authorization_code = models.CharField(max_length=100)
    card_type = models.CharField(max_length=50)
    last4 = models.CharField(max_length=4)
    exp_month = models.CharField(max_length=2)
    exp_year = models.CharField(max_length=4)
    bank = models.CharField(max_length=100)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.is_primary:
            PaymentCard.objects.filter(store=self.store).exclude(id=self.id).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.card_type.capitalize()} card ending in {self.last4} ({self.store.name})"
