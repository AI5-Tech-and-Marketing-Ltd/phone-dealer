import uuid
from decimal import Decimal
from django.utils import timezone
from rest_framework import viewsets, permissions, status, views, decorators
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample
from .models import Plan, Subscription, Bill
from stores.models import Store
from .serializers import (
    PlanSerializer, SubscriptionSerializer, BillSerializer, 
    CreateSubscriptionBillSerializer, BillCheckoutResponseSerializer
)

def apply_bill_action(bill):
    if bill.status == 'Paid':
        return # Idempotent safety
        
    bill.status = 'Paid'
    bill.paid_at = timezone.now()
    bill.save()
        
    sub = bill.subscription
    if sub:
        sub.payment_status = 'Paid'
        if bill.bill_type == 'StaffAddition':
             sub.max_staff += bill.staff_count_change
             sub.next_billing_amount += (bill.staff_count_change * sub.plan.price_per_user)
        elif bill.bill_type in ['NewSubscription', 'Renewal']:
             # In a real app, renewal/expiry logic would go here
             pass
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
    responses={201: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            'Create Subscription Bill Example',
            value={'plan_id': 1, 'staff_count': 5},
            request_only=True
        )
    ]
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
    responses={200: BillCheckoutResponseSerializer},
    examples=[
        OpenApiExample(
            'Pay Bill Response Example',
            value={
                "checkout_url": "https://checkout.paystack.com/access_code",
                "reference": "SUB-1234567890",
                "amount": 5000.0,
                "access_code": "access_code"
            },
            response_only=True
        )
    ]
)
class PayBillView(views.APIView):
    from accounts.permissions import IsStoreOwner
    permission_classes = [IsStoreOwner]

    def post(self, request, pk):
        try:
            bill = Bill.objects.get(id=pk, store__owner=request.user, status='Pending')
            
            import requests
            from django.conf import settings
            
            url = "https://api.paystack.co/transaction/initialize"
            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json"
            }
            # Amount in kobo
            payload = {
                "email": request.user.email,
                "amount": int(bill.amount * 100),
                "reference": bill.reference,
                "callback_url": f"{settings.FRONTEND_URL}/subscription/verify",
                "metadata": {
                    "bill_id": bill.id
                }
            }
            
            try:
                response = requests.post(url, json=payload, headers=headers)
                data = response.json()
                
                if data.get('status'):
                    return Response({
                        "checkout_url": data['data']['authorization_url'],
                        "reference": bill.reference,
                        "amount": float(bill.amount),
                        "access_code": data['data']['access_code']
                    })
                return Response({"error": "Paystack initialization failed", "details": data}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({"error": f"Payment provider error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
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

@extend_schema(
    tags=['Payments'], 
    request=OpenApiTypes.OBJECT, 
    responses={200: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            'Paystack Webhook Example',
            value={
                "event": "charge.success",
                "data": {
                    "reference": "SUB-1234567890",
                    "status": "success",
                    "amount": 500000
                }
            },
            request_only=True
        )
    ]
)
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
        if data.get('event') == 'charge.success':
            reference = data['data']['reference']
            try:
                bill = Bill.objects.get(reference=reference)
                if bill.status == 'Pending':
                    apply_bill_action(bill)
            except Bill.DoesNotExist: pass
                
        return Response(status=200)
