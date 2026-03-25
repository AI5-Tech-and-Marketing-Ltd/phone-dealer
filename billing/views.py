import uuid
from decimal import Decimal
from django.utils import timezone
from rest_framework import viewsets, permissions, status, views, decorators
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from .models import Plan, Subscription, Bill
from stores.models import Store
from .serializers import (
    PlanSerializer, SubscriptionSerializer, BillSerializer, 
    CreateSubscriptionBillSerializer
)

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

@extend_schema(tags=['Plans'])
class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """Public list of available subscription plans."""
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]

@extend_schema(tags=['Subscriptions'])
class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    queryset = Subscription.objects.all()

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAdminUser()]
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

@extend_schema(
    tags=['Subscriptions'], 
    request=CreateSubscriptionBillSerializer,
    responses={201: OpenApiTypes.OBJECT}
)
class CreateSubscriptionBillView(views.APIView):
    from accounts.permissions import IsStoreOwner
    permission_classes = [IsStoreOwner]

    def post(self, request):
        serializer = CreateSubscriptionBillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        store = Store.objects.filter(owner=request.user).first()
        if not store:
            return Response({"error": "You must own a store to subscribe."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            plan = Plan.objects.get(id=serializer.validated_data['plan_id'], is_active=True)
        except Plan.DoesNotExist:
            return Response({"error": "Plan not found."}, status=status.HTTP_404_NOT_FOUND)
        
        staff_count = serializer.validated_data['staff_count']
        total_amount = plan.price_per_user * staff_count
        exp_date = timezone.now().date() + timezone.timedelta(days=plan.renewal_period_days)
        
        sub, created = Subscription.objects.update_or_create(
            store=store,
            defaults={
                'plan': plan,
                'max_staff': staff_count,
                'expiry_date': exp_date,
                'payment_status': 'Pending',
                'next_billing_amount': total_amount,
                'reduced_slots_balance': 0
            }
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

@extend_schema(
    tags=['Billing'],
    parameters=[OpenApiParameter(name='pk', type=int, location='path', description='Bill ID')],
    request=None,
    responses={200: OpenApiTypes.OBJECT}
)
class PayBillView(views.APIView):
    from accounts.permissions import IsStoreOwner
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

@extend_schema(tags=['Payments'], responses={200: OpenApiTypes.OBJECT})
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

@extend_schema(tags=['Payments'], request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class PaystackWebhookView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        import hmac, hashlib
        from django.conf import settings
        
        signature = request.headers.get('x-paystack-signature')
        if not signature: return Response(status=400)
            
        payload = request.body
        computed_signature = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
            payload, hashlib.sha512
        ).hexdigest()
        
        if computed_signature != signature: return Response(status=400)
            
        data = request.data
        if data['event'] == 'charge.success':
            reference = data['data']['reference']
            try:
                bill = Bill.objects.get(reference=reference)
                if bill.status == 'Pending':
                    apply_bill_action(bill)
            except Bill.DoesNotExist: pass
                
        return Response(status=200)
