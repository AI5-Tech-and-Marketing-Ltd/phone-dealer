import uuid
from decimal import Decimal
from django.utils import timezone
from rest_framework import viewsets, permissions, status, views, decorators
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample
from .models import Plan, Subscription, Bill, PaymentCard
from stores.models import Store
from .serializers import (
    PlanSerializer, SubscriptionSerializer, BillSerializer, 
    CreateSubscriptionBillSerializer, BillCheckoutResponseSerializer,
    PaymentCardSerializer, AutoRenewSerializer
)

def initialize_paystack_payment(request, bill):
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
            "bill_id": bill.id,
            "save_card": bill.save_card
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    except Exception as e:
        return {"status": False, "message": str(e)}

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

def handle_payment_success(bill, auth_data=None):
    """Marks bill as paid and optionally saves card authorization."""
    if bill.status == 'Pending':
        apply_bill_action(bill)
    
    if auth_data and auth_data.get('reusable'):
        should_save = bill.save_card or (bill.bill_type == 'CardTokenization')
        if should_save:
            PaymentCard.objects.update_or_create(
                store=bill.store,
                authorization_code=auth_data['authorization_code'],
                defaults={
                    'card_type': auth_data['card_type'],
                    'last4': auth_data['last4'],
                    'exp_month': auth_data['exp_month'],
                    'exp_year': auth_data['exp_year'],
                    'bank': auth_data['bank'],
                    'is_primary': not PaymentCard.objects.filter(store=bill.store).exists()
                }
            )

@extend_schema(tags=['Plans'])
class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """Public list of available subscription plans."""
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]

@extend_schema(tags=['Subscriptions'])
class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubscriptionSerializer
    queryset = Subscription.objects.all()

    from accounts.permissions import IsStoreOwner
    permission_classes = [IsStoreOwner]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Subscription.objects.none()
        return Subscription.objects.filter(store__owner=self.request.user)
    

    @decorators.action(detail=False, methods=['get'])
    def me(self, request):
        store = Store.objects.filter(owner=request.user).first()
        if not store:
            return Response({"error": "No store found."}, status=404)
        try:
            sub = store.subscription
            return Response(self.get_serializer(sub).data)
        except Subscription.DoesNotExist:
            return Response({"error": "No subscription found."}, status=404)

@extend_schema(tags=['Billing'])
class BillViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BillSerializer
    from accounts.permissions import IsStoreOwner
    permission_classes = [IsStoreOwner]

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
            value={'plan_id': 1, 'staff_count': 5, 'save_card': True, 'auto_renew': True},
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
                'reduced_slots_balance': 0,
                'auto_renew': serializer.validated_data.get('auto_renew', False)
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

        # Handle auto-save logic: if auto_renew is on, save card by default
        save_card = serializer.validated_data.get('save_card', False)
        if sub.auto_renew:
            save_card = True
        
        if save_card:
            bill.save_card = True
            bill.save()
        
        # Auto-initiate Paystack payment
        paystack_data = initialize_paystack_payment(request, bill)
        
        response_data = {
            "bill": BillSerializer(bill).data,
            "subscription": SubscriptionSerializer(sub).data
        }

        if paystack_data.get('status'):
            response_data.update({
                "checkout_url": paystack_data['data']['authorization_url'],
                "access_code": paystack_data['data']['access_code'],
                "reference": bill.reference
            })
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response({
            "error": "Subscription created but payment initialization failed",
            "details": paystack_data,
            "bill": BillSerializer(bill).data
        }, status=status.HTTP_201_CREATED)

@extend_schema(
    tags=['Billing'],
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
            
            # Guard: don't retry if a newer paid bill of same type already exists
            newer_paid = Bill.objects.filter(
                store=bill.store,
                bill_type=bill.bill_type,
                status='Paid',
                created_at__gt=bill.created_at
            ).exists()

            if newer_paid:
                return Response({"error": "A newer paid bill already exists for this type."}, status=status.HTTP_400_BAD_REQUEST)

             # Regenerate reference to avoid Paystack duplicate_reference error
            prefix = bill.bill_type[:3].upper() if bill.bill_type else "BIL"
            bill.reference = f"{prefix}-{uuid.uuid4().hex[:10].upper()}"
            bill.save()

            paystack_data = initialize_paystack_payment(request, bill)
            
            if paystack_data.get('status'):
                return Response({
                    "checkout_url": paystack_data['data']['authorization_url'],
                    "reference": bill.reference,
                    "amount": float(bill.amount),
                    "access_code": paystack_data['data']['access_code']
                })
            return Response({"error": "Paystack initialization failed", "details": paystack_data}, status=status.HTTP_400_BAD_REQUEST)
                
        except Bill.DoesNotExist:
             return Response({"error": "Pending bill not found."}, status=status.HTTP_404_NOT_FOUND)

@extend_schema(
    tags=['Payments'], 
    request=OpenApiTypes.OBJECT,
    responses={200: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            'Callback Example',
            value={
                'trxref': 'TKN-ABC123XYZ',
                'reference': 'TKN-ABC123XYZ'
            },
            request_only=True
        )
    ]
)
class PaystackCallbackView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        reference = request.data.get('reference')
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
                auth_data = data['data'].get('authorization')
                handle_payment_success(bill, auth_data)
                
                return Response({
                    "status": "success",
                    "message": "Payment verified and applied.",
                    "bill": BillSerializer(bill).data,
                    "subscription": SubscriptionSerializer(bill.subscription).data if bill.subscription else None
                })
            except Bill.DoesNotExist:
                return Response({"error": "Bill not found"}, status=404)
        
        return Response({"status": "failed", "error": "Payment verification failed"}, status=400)

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
                auth_data = data['data'].get('authorization')
                handle_payment_success(bill, auth_data)
            except Bill.DoesNotExist: pass
                
        return Response(status=200)

@extend_schema(tags=['Billing'])
class PaymentCardViewSet(viewsets.ReadOnlyModelViewSet, viewsets.mixins.DestroyModelMixin, viewsets.mixins.UpdateModelMixin):
    """Manage saved payment cards for the store."""
    serializer_class = PaymentCardSerializer
    from accounts.permissions import IsStoreOwner
    permission_classes = [IsStoreOwner]
    http_method_names = ['get', 'delete', 'post', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
             return PaymentCard.objects.none()
        return PaymentCard.objects.filter(store__owner=self.request.user)

    @decorators.action(detail=True, methods=['POST'], url_path='set-primary')
    def set_primary(self, request, pk=None):
        card = self.get_object()
        card.is_primary = True
        card.save()
        return Response({"message": f"Card ending in {card.last4} set as primary."})

@extend_schema(
    tags=['Subscriptions'], 
    request=AutoRenewSerializer,
    responses={200: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            'Auto Renew Toggle Example',
            value={'auto_renew': True},
            request_only=True
        )
    ]
)
class AutoRenewToggleView(views.APIView):
    """Toggle auto-renewal for the store's subscription."""
    from accounts.permissions import IsStoreOwner
    permission_classes = [IsStoreOwner]

    def patch(self, request):
        serializer = AutoRenewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        store = Store.objects.filter(owner=request.user).first()
        if not store or not hasattr(store, 'subscription'):
             return Response({"error": "No subscription found."}, status=status.HTTP_404_NOT_FOUND)
        
        sub = store.subscription
        sub.auto_renew = serializer.validated_data['auto_renew']
        sub.save()
        
        return Response({
            "message": f"Auto-renew {'enabled' if sub.auto_renew else 'disabled'}.",
            "auto_renew": sub.auto_renew
        })

@extend_schema(tags=['Billing'], responses={201: BillCheckoutResponseSerializer})
class InitiateCardTokenizationView(views.APIView):
    """Initiate a small charge (NGN 50) to save and verify a card."""
    from accounts.permissions import IsStoreOwner
    permission_classes = [IsStoreOwner]

    def post(self, request):
        store = Store.objects.filter(owner=request.user).first()
        if not store:
            return Response({"error": "Store not found."}, status=404)
        
        bill = Bill.objects.create(
            store=store,
            bill_type='CardTokenization',
            amount=Decimal('50.00'),
            reference=f"TKN-{uuid.uuid4().hex[:10].upper()}",
            description="Card Tokenization / Verification Charge",
            save_card=True,
            status='Pending'
        )

        paystack_data = initialize_paystack_payment(request, bill)
        if paystack_data.get('status'):
            return Response({
                "checkout_url": paystack_data['data']['authorization_url'],
                "reference": bill.reference,
                "amount": float(bill.amount),
                "access_code": paystack_data['data']['access_code']
            }, status=status.HTTP_201_CREATED)
        
        return Response({"error": "Paystack initialization failed", "details": paystack_data}, status=status.HTTP_400_BAD_REQUEST)
