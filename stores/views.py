import uuid
from decimal import Decimal
from django.utils import timezone
from rest_framework import viewsets, permissions, status, views, decorators
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample
from .models import Store
from billing.models import Plan, Subscription, Bill
from billing.serializers import BillSerializer, StoreAddStaffSerializer, ReduceStaffSerializer
from accounts.models import CustomUser
from accounts.serializers import UserSerializer, AddStaffSerializer as AccountAddStaffSerializer
from accounts.permissions import IsStoreOwner, IsStoreKeeper, IsSuperUser
from billing.permissions import HasActiveSubscription
from .analytics_utils import get_store_analytics

@extend_schema(tags=['Stores'])
class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer # Placeholder for StoreSerializer if needed
    from .serializers import StoreSerializer
    serializer_class = StoreSerializer
    queryset = Store.objects.all()

    def get_permissions(self):
        # StoreOwner: all operations. StoreKeeper: Get only.
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
             return [permissions.IsAuthenticated(), IsStoreOwner(), HasActiveSubscription()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False): return Store.objects.none()
        if self.request.user.role == 'SuperUser': return Store.objects.all()
        # Owners and Keepers can see their respective store
        return Store.objects.filter(
            permissions.models.Q(owner=self.request.user) | 
            permissions.models.Q(staff_users=self.request.user) |
            permissions.models.Q(id=getattr(self.request.user, 'store_id', None))
        ).distinct()
        # Simplified for now since CustomUser has store field or stores related name

    @decorators.action(detail=False, methods=['get'])
    def me(self, request):
        if request.user.role == 'StoreOwner':
            store = Store.objects.filter(owner=request.user).first()
        else:
            store = getattr(request.user, 'store', None)
            
        if not store: return Response({"error": "Store not found."}, status=404)
        serializer = self.get_serializer(store)
        return Response(serializer.data)

@extend_schema(tags=['Stores'], parameters=[OpenApiParameter("email", type=str, location="path", description="Staff email")])
class StoreStaffViewSet(viewsets.ModelViewSet):
    lookup_field = 'email'
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False): return CustomUser.objects.none()
        return CustomUser.objects.filter(store__owner=self.request.user)
    
    def perform_create(self, serializer):
        store = Store.objects.filter(owner=self.request.user).first()
        serializer.save(store=store, role='StoreKeeper')

@extend_schema(
    tags=['Subscriptions'], 
    request=StoreAddStaffSerializer, 
    responses={201: BillSerializer},
    examples=[
        OpenApiExample(
            'Add Staff Slots Example',
            value={'count': 2},
            request_only=True
        )
    ]
)
class AddStaffView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def post(self, request):
        serializer = StoreAddStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        store = Store.objects.filter(owner=request.user).first()
        if not store: return Response({"error": "Store not found."}, status=404)
        
        try:
            sub = store.subscription
            if sub.payment_status != 'Paid': return Response({"error": "No active/paid subscription found."}, status=400)
        except Subscription.DoesNotExist: return Response({"error": "No subscription found."}, status=400)
        
        plan = sub.plan
        adding_count = serializer.validated_data['count']
        restorable = sub.reduced_slots_balance
        
        if adding_count <= restorable:
            sub.max_staff += adding_count
            sub.reduced_slots_balance -= adding_count
            sub.save()
            return Response({"message": f"Successfully restored {adding_count} slots.", "max_staff": sub.max_staff})
        
        already_restored = restorable
        to_bill_count = adding_count - already_restored
        if already_restored > 0:
            sub.max_staff += already_restored
            sub.reduced_slots_balance = 0
            sub.save()

        days_left = (sub.expiry_date - timezone.now().date()).days
        if days_left <= 0: days_left = 1
        total_amount = ( (plan.price_per_user * Decimal(days_left)) / Decimal(plan.renewal_period_days) * Decimal(to_bill_count) ).quantize(Decimal('0.01'))
        
        bill = Bill.objects.create(
            store=store, subscription=sub, plan=plan, bill_type='StaffAddition', amount=total_amount,
            reference=f"ADD-{uuid.uuid4().hex[:8].upper()}", staff_count_change=to_bill_count,
            description=f"Addition of {to_bill_count} staff slots."
        )
        return Response(BillSerializer(bill).data, status=status.HTTP_201_CREATED)

@extend_schema(
    tags=['Subscriptions'], 
    request=ReduceStaffSerializer, 
    responses={200: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            'Reduce Staff Slots Example',
            value={'count': 1},
            request_only=True
        )
    ]
)
class ReduceStaffView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def post(self, request):
        serializer = ReduceStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        store = Store.objects.filter(owner=request.user).first()
        if not store: return Response({"error": "Store not found."}, status=404)
        
        try:
            sub = store.subscription
        except Subscription.DoesNotExist: return Response({"error": "No subscription found."}, status=400)
        
        count = serializer.validated_data['count']
        if sub.max_staff - count < 2: return Response({"error": "Cannot reduce below 2."}, status=400)
        
        sub.max_staff -= count
        sub.reduced_slots_balance += count
        sub.next_billing_amount -= (count * sub.plan.price_per_user)
        if sub.next_billing_amount < 0: sub.next_billing_amount = Decimal('0.00')
        sub.save()
        return Response({"message": f"Reduced by {count}.", "max_staff": sub.max_staff})

@extend_schema(
    tags=['Stores'], 
    request=AccountAddStaffSerializer, 
    responses={201: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            'Create Staff Account Example',
            value={
                'email': 'staff@example.com',
                'full_name': 'John Staff',
                'phone_number': '08012345678',
                'password': 'staffpassword123'
            },
            request_only=True
        )
    ]
)
class StoreStaffCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def post(self, request):
        serializer = AccountAddStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        store = Store.objects.filter(owner=request.user).first()
        if not store: return Response({"error": "No store found."}, status=400)
        
        try:
            sub = store.subscription
            limit = sub.max_staff
        except: limit = 2

        if CustomUser.objects.filter(store=store).count() >= limit:
             return Response({"error": f"Limit reached ({limit})."}, status=400)
            
        user = serializer.save()
        user.is_active = True
        user.role = 'StoreKeeper'
        user.store = store
        user.save()
        return Response({"message": "Staff created.", "user": UserSerializer(user).data})

@extend_schema(
    tags=['Stores'],
    parameters=[
        OpenApiParameter("start_date", type=str, location="query", description="YYYY-MM-DD"),
        OpenApiParameter("end_date", type=str, location="query", description="YYYY-MM-DD"),
        OpenApiParameter("group_by", type=str, location="query", enum=['daily', 'weekly', 'monthly', 'annually']),
    ],
    responses={200: OpenApiTypes.OBJECT}
)
class AnalyticsView(views.APIView):
    """Business Intelligence for Store Owners."""
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def get(self, request):
        if request.user.role == 'StoreOwner':
            store = Store.objects.filter(owner=request.user).first()
        else:
            store = getattr(request.user, 'store', None)
            
        if not store:
            return Response({"error": "No store found."}, status=404)
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        group_by = request.query_params.get('group_by', 'daily')
        
        data = get_store_analytics(store, start_date, end_date, group_by)
        return Response(data)
