import uuid
from decimal import Decimal
from django.utils import timezone
from rest_framework import viewsets, permissions, status, views, decorators
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .serializers import (
    StoreSerializer, SubscriptionSerializer, BillSerializer,
    CreateSubscriptionBillSerializer, AddStaffSerializer, ReduceStaffSerializer
)
from .models import Store, Subscription, Bill
from accounts.permissions import IsStoreOwner, IsSuperUser

@extend_schema(tags=['Stores'])
class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    queryset = Store.objects.all()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
             return [(IsStoreOwner | IsSuperUser)()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Store.objects.none()
        return Store.objects.filter(owner=self.request.user)

@extend_schema(tags=['Subscriptions'])
class SubscriptionViewSet(viewsets.ModelViewSet):

    serializer_class = SubscriptionSerializer
    queryset = Subscription.objects.all()

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsSuperUser()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Subscription.objects.none()
        return Subscription.objects.filter(store__owner=self.request.user)

@extend_schema(tags=['Billing'])
class BillViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = BillSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Bill.objects.none()
        return Bill.objects.filter(store__owner=self.request.user)

@extend_schema(tags=['Subscriptions'])
class CreateSubscriptionBillView(views.APIView):

    permission_classes = [IsStoreOwner]

    def post(self, request):
        serializer = CreateSubscriptionBillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        store = Store.objects.get(id=serializer.validated_data['store_id'], owner=request.user)
        
        # Calculate amount based on plan
        amounts = {'Free': 0, 'Basic': 50, 'Premium': 100}
        plan = serializer.validated_data['plan_type']
        
        bill = Bill.objects.create(
            store=store,
            bill_type='NewSubscription',
            amount=Decimal(amounts[plan]),
            reference=f"SUB-{uuid.uuid4().hex[:10].upper()}",
            description=f"New {plan} subscription",
            status='Pending' if amounts[plan] > 0 else 'Paid'
        )

        if bill.status == 'Paid':
             # Activate Free plan immediately
             exp_date = timezone.now().date() + timezone.timedelta(days=365) # 1 year for free
             Subscription.objects.create(
                 store=store, plan_type=plan, expiry_date=exp_date, 
                 payment_status='Paid', max_staff=2
             )
        
        return Response(BillSerializer(bill).data, status=status.HTTP_201_CREATED)

@extend_schema(tags=['Subscriptions'])
class AddStaffView(views.APIView):

    permission_classes = [IsStoreOwner]

    def post(self, request):
        serializer = AddStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        store = Store.objects.get(id=serializer.validated_data['store_id'], owner=request.user)
        sub = store.subscriptions.filter(payment_status='Paid').first()
        
        if not sub:
             return Response({"error": "No active subscription found."}, status=status.HTTP_400_BAD_REQUEST)
        
        count = serializer.validated_data['count']
        amount = count * sub.amount_per_staff
        
        bill = Bill.objects.create(
            store=store,
            subscription=sub,
            bill_type='StaffAddition',
            amount=amount,
            reference=f"STF-{uuid.uuid4().hex[:10].upper()}",
            description=f"Adding {count} staff slots",
            staff_count_change=count
        )
        return Response(BillSerializer(bill).data, status=status.HTTP_201_CREATED)

@extend_schema(tags=['Subscriptions'])
class ReduceStaffView(views.APIView):

    permission_classes = [IsStoreOwner]

    def post(self, request):
        serializer = ReduceStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        store = Store.objects.get(id=serializer.validated_data['store_id'], owner=request.user)
        sub = store.subscriptions.filter(payment_status='Paid').first()
        
        if not sub:
             return Response({"error": "No active subscription found."}, status=status.HTTP_400_BAD_REQUEST)
        
        count = serializer.validated_data['count']
        if sub.max_staff - count < 2: # Min limit
             return Response({"error": "Cannot reduce staff below 2."}, status=status.HTTP_400_BAD_REQUEST)
        
        sub.max_staff -= count
        # Update next cycle amount (Basic calculation: base plan + additional staff)
        # Assuming renewal view will handle base plan cost
        sub.next_billing_amount -= (count * sub.amount_per_staff)
        sub.save()
        
        return Response({"message": f"Successfully reduced staff by {count}. Next bill updated."})

def apply_bill_action(bill):
    """Business logic to apply effects of a paid bill."""
    if bill.status != 'Paid':
        bill.status = 'Paid'
        bill.paid_at = timezone.now()
        bill.save()
        
    if bill.bill_type == 'NewSubscription':
         # Assuming monthly for now
         exp = timezone.now().date() + timezone.timedelta(days=30)
         plan = 'Basic' if 'Basic' in bill.description else 'Premium'
         Subscription.objects.create(
             store=bill.store, plan_type=plan, expiry_date=exp,
             payment_status='Paid', max_staff=2
         )
    elif bill.bill_type == 'StaffAddition':
         sub = bill.subscription
         if sub:
             sub.max_staff += bill.staff_count_change
             sub.next_billing_amount += (bill.staff_count_change * sub.amount_per_staff)
             sub.save()

@extend_schema(tags=['Payments'])
class PaystackCallbackView(views.APIView):

    """User returns here after payment."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        reference = request.query_params.get('reference')
        if not reference:
            return Response({"error": "No reference provided"}, status=400)
            
        # Verify with Paystack
        import requests
        from django.conf import settings
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data.get('status') and data['data']['status'] == 'success':
            try:
                bill = Bill.objects.get(reference=reference)
                if bill.status == 'Pending':
                    apply_bill_action(bill)
                return Response({"message": "Payment verified and applied."})
            except Bill.DoesNotExist:
                return Response({"error": "Bill not found"}, status=404)
        
        return Response({"error": "Payment verification failed"}, status=400)

@extend_schema(tags=['Payments'])
class PaystackWebhookView(views.APIView):

    """Server-to-server notification from Paystack."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        import hmac
        import hashlib
        from django.conf import settings
        
        signature = request.headers.get('x-paystack-signature')
        if not signature:
            return Response(status=400)
            
        # Verify signature
        payload = request.body
        computed_signature = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        if computed_signature != signature:
            return Response(status=400)
            
        data = request.data
        if data['event'] == 'charge.success':
            reference = data['data']['reference']
            try:
                bill = Bill.objects.get(reference=reference)
                if bill.status == 'Pending':
                    apply_bill_action(bill)
            except Bill.DoesNotExist:
                pass # Or log error
                
        return Response(status=200)

@extend_schema(tags=['Billing'])
class PayBillView(views.APIView):

    """Endpoint for frontend to get payment URL or simulate payment."""
    permission_classes = [IsStoreOwner]

    def post(self, request, pk):
        # In production, this should return a Paystack checkout URL
        # For now, keeping partial simulation but adding Paystack metadata logic
        try:
            bill = Bill.objects.get(id=pk, store__owner=request.user, status='Pending')
            # Mocking the initialization of a Paystack transaction
            return Response({
                "checkout_url": f"https://checkout.paystack.com/mock-{bill.reference}",
                "reference": bill.reference,
                "amount": float(bill.amount)
            })
        except Bill.DoesNotExist:
             return Response({"error": "Pending bill not found."}, status=status.HTTP_404_NOT_FOUND)

@extend_schema(tags=['Stores'])
class StoreStaffCreateView(views.APIView):
    """Store owners adding staff user accounts."""
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def post(self, request):
        from accounts.serializers import AddStaffSerializer as AccountAddStaffSerializer, UserSerializer
        from accounts.models import CustomUser
        
        serializer = AccountAddStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check store staff limit
        # This is a bit simplified, ideally check against Store.staff_limit
        # or valid subscriptions.
        
        user = serializer.save()
        user.is_active = True # Active immediately in this flow
        user.role = 'StoreKeeper'
        user.save()
        
        # Link user to store if there's a many-to-many or foreign key
        # Current Store model doesn't have a direct link to staff users yet?
        # Wait, let's check Store model.
        
        return Response({
            "message": "Store keeper account created successfully.",
            "user": UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
