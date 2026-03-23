import uuid
from decimal import Decimal
from django.utils import timezone
from rest_framework import viewsets, permissions, status, views, decorators
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .serializers import (
    StoreSerializer, SubscriptionSerializer, BillSerializer, PlanSerializer,
    CreateSubscriptionBillSerializer, AddStaffSerializer, ReduceStaffSerializer
)
from .models import Store, Subscription, Bill, Plan
from accounts.models import CustomUser
from accounts.serializers import UserSerializer
from accounts.permissions import IsStoreOwner, IsSuperUser

@extend_schema(tags=['Plans'])
class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """Public list of available subscription plans."""
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]

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
        if self.request.user.role == 'SuperUser':
            return Store.objects.all()
        return Store.objects.filter(owner=self.request.user)

@extend_schema(tags=['Stores'])
class StoreStaffViewSet(viewsets.ModelViewSet):
    """Manage staff users linked to the store."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
             return CustomUser.objects.none()
        return CustomUser.objects.filter(store__owner=self.request.user)
    
    def perform_create(self, serializer):
        store = Store.objects.filter(owner=self.request.user).first()
        serializer.save(store=store, role='StoreKeeper')

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
        
        try:
            store = Store.objects.get(id=serializer.validated_data['store_id'], owner=request.user)
            plan = Plan.objects.get(id=serializer.validated_data['plan_id'], is_active=True)
        except (Store.DoesNotExist, Plan.DoesNotExist):
            return Response({"error": "Store or Plan not found."}, status=status.HTTP_404_NOT_FOUND)
        
        staff_count = serializer.validated_data['staff_count']
        total_amount = plan.price_per_user * staff_count
        
        # Create pending subscription
        # Expire in 30 days if new
        exp_date = timezone.now().date() + timezone.timedelta(days=plan.renewal_period_days)
        
        sub = Subscription.objects.create(
            store=store,
            plan=plan,
            max_staff=staff_count,
            expiry_date=exp_date,
            payment_status='Pending',
            next_billing_amount=total_amount
        )
        
        bill = Bill.objects.create(
            store=store,
            subscription=sub,
            plan=plan,
            bill_type='NewSubscription',
            amount=total_amount,
            reference=f"SUB-{uuid.uuid4().hex[:10].upper()}",
            description=f"{plan.title} subscription for {staff_count} staff slots",
            status='Pending'
        )
        
        return Response({
            "bill": BillSerializer(bill).data,
            "subscription": SubscriptionSerializer(sub).data
        }, status=status.HTTP_201_CREATED)

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
        
        plan = sub.plan
        if not plan:
             return Response({"error": "Subscription plan not found."}, status=status.HTTP_400_BAD_REQUEST)
             
        count = serializer.validated_data['count']
        amount = count * plan.price_per_user
        
        bill = Bill.objects.create(
            store=store,
            subscription=sub,
            plan=plan,
            bill_type='StaffAddition',
            amount=amount,
            reference=f"STF-{uuid.uuid4().hex[:10].upper()}",
            description=f"Adding {count} staff slots to {plan.title}",
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
        
        plan = sub.plan
        if not plan:
             return Response({"error": "Subscription plan not found."}, status=status.HTTP_400_BAD_REQUEST)

        count = serializer.validated_data['count']
        if sub.max_staff - count < 2:
             return Response({"error": "Cannot reduce staff below 2."}, status=status.HTTP_400_BAD_REQUEST)
        
        sub.max_staff -= count
        sub.next_billing_amount -= (count * plan.price_per_user)
        sub.save()
        
        return Response({"message": f"Successfully reduced staff by {count}. Next bill updated."})

def apply_bill_action(bill):
    if bill.status != 'Paid':
        bill.status = 'Paid'
        bill.paid_at = timezone.now()
        bill.save()
        
    sub = bill.subscription
    if sub:
        sub.payment_status = 'Paid'
        if bill.bill_type == 'StaffAddition':
             sub.max_staff += bill.staff_count_change
             sub.next_billing_amount += (bill.staff_count_change * sub.plan.price_per_user)
        sub.save()

@extend_schema(tags=['Payments'])
class PaystackCallbackView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        reference = request.query_params.get('reference')
        if not reference:
            return Response({"error": "No reference provided"}, status=400)
            
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
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        import hmac
        import hashlib
        from django.conf import settings
        
        signature = request.headers.get('x-paystack-signature')
        if not signature:
            return Response(status=400)
            
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
                pass
                
        return Response(status=200)

@extend_schema(tags=['Billing'])
class PayBillView(views.APIView):
    permission_classes = [IsStoreOwner]

    def post(self, request, pk):
        try:
            bill = Bill.objects.get(id=pk, store__owner=request.user, status='Pending')
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
        
        serializer = AccountAddStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        store = Store.objects.filter(owner=request.user).first()
        if not store:
            return Response({"error": "You must own a store to add staff."}, status=400)
            
        user = serializer.save()
        user.is_active = True
        user.role = 'StoreKeeper'
        user.store = store
        user.save()
        
        return Response({
            "message": "Store keeper account created successfully.",
            "user": UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
