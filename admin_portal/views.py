from django.utils import timezone
from rest_framework import views, viewsets, permissions, status, serializers, decorators
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from accounts.models import CustomUser
from accounts.serializers import UserSerializer
from accounts.permissions import IsSuperUser
from stores.models import Store
from billing.models import Subscription, Bill, Plan
from billing.serializers import SubscriptionSerializer, BillSerializer, PlanSerializer
from stores.serializers import StoreSerializer
from inventory.models import Product, Allocation
from inventory.serializers import ProductSerializer, AllocationSerializer
from .serializers import AssignStoreSerializer, ChangeOwnerSerializer, AdminUserCreateSerializer, DashboardStatsSerializer

@extend_schema(tags=['Admin Portal - Dashboard'], responses=DashboardStatsSerializer)
class DashboardStatsView(views.APIView):
    """System-wide analytics for Super Admins."""
    permission_classes = [IsSuperUser]
    
    def get(self, request):
        from django.db.models import Sum
        total_revenue = Bill.objects.filter(status='Paid').aggregate(Sum('amount'))['amount__sum'] or 0.00
        return Response({
            "total_users": CustomUser.objects.count(),
            "total_stores": Store.objects.count(),
            "total_products": Product.objects.count(),
            "active_subscriptions": Subscription.objects.filter(expiry_date__gte=timezone.now().date()).count(),
            "total_revenue": total_revenue
        })

@extend_schema(tags=['Admin Portal - Users'], parameters=[OpenApiParameter("email", type=str, location="path", description="User email")])
class UserManagementViewSet(viewsets.ModelViewSet):
    """Full user CRUD for Super Admins."""
    lookup_field = 'email'
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSuperUser]

    def get_serializer_class(self):
        if self.action == 'create': return AdminUserCreateSerializer
        return UserSerializer

    @extend_schema(request=AssignStoreSerializer)
    @decorators.action(detail=True, methods=['POST'], url_path='assign-store')
    def assign_store(self, request, pk=None):
        """Add/Update/Remove a user from a store and change role."""
        user = self.get_object()
        serializer = AssignStoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        store_id = serializer.validated_data.get('store_id')
        role = serializer.validated_data.get('role')
        if store_id is not None:
            try:
                store = Store.objects.get(id=store_id)
                user.store = store
            except Store.DoesNotExist:
                 return Response({"error": "Store not found."}, status=status.HTTP_404_NOT_FOUND)
        else: user.store = None
        if role: user.role = role
        user.save()
        return Response(UserSerializer(user).data)

@extend_schema(tags=['Admin Portal - Stores'])
class AdminStoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [IsSuperUser]

    @extend_schema(request=ChangeOwnerSerializer)
    @decorators.action(detail=True, methods=['POST'], url_path='change-owner')
    def change_owner(self, request, pk=None):
        """Update the store's primary owner."""
        store = self.get_object()
        serializer = ChangeOwnerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_owner_email = serializer.validated_data['new_owner_email']
        try:
            new_owner = CustomUser.objects.get(email=new_owner_email)
            if new_owner.role != 'StoreOwner':
                 new_owner.role = 'StoreOwner'
                 new_owner.save()
            store.owner = new_owner
            store.save()
            return Response(StoreSerializer(store).data)
        except CustomUser.DoesNotExist:
             return Response({"error": "User with this email not found."}, status=status.HTTP_404_NOT_FOUND)

    @decorators.action(detail=True, methods=['GET'], url_path='staff')
    def list_staff(self, request, pk=None):
        """List all users under this store."""
        store = self.get_object()
        staff = CustomUser.objects.filter(store=store)
        return Response(UserSerializer(staff, many=True).data)

@extend_schema(tags=['Admin Portal - Plans'])
class AdminPlanViewSet(viewsets.ModelViewSet):
    """Full CRUD for subscription plans (SuperAdmin only)."""
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = [IsSuperUser]

@extend_schema(tags=['Admin Portal - Subscriptions'])
class AdminSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsSuperUser]

@extend_schema(tags=['Admin Portal - Billing'])
class AdminBillViewSet(viewsets.ModelViewSet):
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    permission_classes = [IsSuperUser]

    @decorators.action(detail=True, methods=['POST'], url_path='manual-pay')
    def manual_pay(self, request, pk=None):
        """Manually mark a bill as paid (SuperAdmin only)."""
        bill = self.get_object()
        if bill.status == 'Paid':
            return Response({"error": "Bill is already paid."}, status=status.HTTP_400_BAD_REQUEST)
        
        from billing.views import apply_bill_action
        apply_bill_action(bill)
        return Response({"message": f"Bill {bill.reference} manually marked as paid.", "bill": BillSerializer(bill).data})

@extend_schema(tags=['Admin Portal - Products'])
class AdminProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsSuperUser]

@extend_schema(tags=['Admin Portal - Allocations'])
class AdminAllocationViewSet(viewsets.ModelViewSet):
    queryset = Allocation.objects.all()
    serializer_class = AllocationSerializer
    permission_classes = [IsSuperUser]
