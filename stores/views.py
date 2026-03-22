import uuid
from decimal import Decimal
from django.utils import timezone
from rest_framework import viewsets, permissions, status, views, decorators
from rest_framework.response import Response
from .serializers import (
    StoreSerializer, SubscriptionSerializer, BillSerializer,
    CreateSubscriptionBillSerializer, AddStaffSerializer, ReduceStaffSerializer
)
from .models import Store, Subscription, Bill
from accounts.permissions import IsStoreOwner, IsSuperUser

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

class BillViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BillSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Bill.objects.none()
        return Bill.objects.filter(store__owner=self.request.user)

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

class PayBillView(views.APIView):
    permission_classes = [IsStoreOwner]

    def post(self, request, pk):
        try:
            bill = Bill.objects.get(id=pk, store__owner=request.user, status='Pending')
            # Here we would normally redirect to a payment gateway
            # Simulating successful payment for now
            bill.status = 'Paid'
            bill.paid_at = timezone.now()
            bill.save()
            
            # Action based on bill type
            if bill.bill_type == 'NewSubscription':
                 # Already handled or create sub here
                 # Assuming monthly for now
                 exp = timezone.now().date() + timezone.timedelta(days=30)
                 # Guessing plan from description for simplicity in this mockup
                 plan = 'Basic' if 'Basic' in bill.description else 'Premium'
                 Subscription.objects.create(
                     store=bill.store, plan_type=plan, expiry_date=exp,
                     payment_status='Paid', max_staff=2
                 )
            elif bill.bill_type == 'StaffAddition':
                 sub = bill.subscription
                 sub.max_staff += bill.staff_count_change
                 sub.next_billing_amount += (bill.staff_count_change * sub.amount_per_staff)
                 sub.save()
                 
            return Response({"message": "Bill paid and action applied."})
        except Bill.DoesNotExist:
             return Response({"error": "Pending bill not found."}, status=status.HTTP_404_NOT_FOUND)
