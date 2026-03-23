from django.utils import timezone
from rest_framework import views, viewsets, permissions, status, serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from accounts.models import CustomUser
from accounts.serializers import UserSerializer
from accounts.permissions import IsSuperUser
from stores.models import Store, Subscription, Bill
from stores.serializers import StoreSerializer, SubscriptionSerializer, BillSerializer
from inventory.models import Product, Allocation
from inventory.serializers import ProductSerializer, AllocationSerializer

@extend_schema(tags=['Admin Portal'])
class DashboardStatsView(views.APIView):
    """System-wide analytics for Super Admins."""
    permission_classes = [IsSuperUser]

    def get(self, request):
        return Response({
            "total_users": CustomUser.objects.count(),
            "total_stores": Store.objects.count(),
            "total_products": Product.objects.count(),
            "active_subscriptions": Subscription.objects.filter(expiry_date__gte=timezone.now().date()).count()
        })

@extend_schema(tags=['Admin Portal - Users'])
class UserManagementViewSet(viewsets.ModelViewSet):
    """Full user CRUD for Super Admins."""
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSuperUser]

@extend_schema(tags=['Admin Portal - Stores'])
class AdminStoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
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
