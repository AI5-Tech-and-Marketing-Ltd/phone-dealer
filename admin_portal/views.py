from django.utils import timezone
from rest_framework import views, viewsets, permissions, status, serializers
from rest_framework.response import Response
from accounts.models import CustomUser
from accounts.serializers import UserSerializer
from accounts.permissions import IsSuperUser
from stores.models import Store, Subscription, Bill
from stores.serializers import StoreSerializer, SubscriptionSerializer, BillSerializer
from inventory.models import Product, Allocation
from inventory.serializers import ProductSerializer, AllocationSerializer
from sales.models import Sale, Customer
from sales.serializers import SaleSerializer, CustomerSerializer

class DashboardStatsView(views.APIView):
    """System-wide analytics for Super Admins."""
    permission_classes = [IsSuperUser]

    def get(self, request):
        return Response({
            "total_users": CustomUser.objects.count(),
            "total_stores": Store.objects.count(),
            "total_products": Product.objects.count(),
            "total_sales": Sale.objects.count(),
            "active_subscriptions": Subscription.objects.filter(expiry_date__gte=timezone.now().date()).count()
        })

class UserManagementViewSet(viewsets.ModelViewSet):
    """Full user CRUD for Super Admins."""
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSuperUser]

    def perform_create(self, serializer):
        # Even SuperUsers can't create another SuperUser unless they themselves are one 
        # (permissions already check for IsSuperUser, but this is an extra logic check)
        new_role = self.request.data.get('role')
        if new_role == 'SuperUser' and not self.request.user.role == 'SuperUser':
             # This block is technically unreachable due to IsSuperUser permission,
             # but good for explicit logic if we change permissions later.
             raise serializers.ValidationError({"error": "Only a SuperUser can create another SuperUser."})
        serializer.save()

    def perform_update(self, serializer):
        old_role = self.get_object().role
        new_role = self.request.data.get('role')
        if new_role == 'SuperUser' and old_role != 'SuperUser' and not self.request.user.role == 'SuperUser':
             raise serializers.ValidationError({"error": "Only a SuperUser can promote a user to SuperUser."})
        serializer.save()

class AdminStoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [IsSuperUser]

class AdminSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsSuperUser]

class AdminBillViewSet(viewsets.ModelViewSet):
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    permission_classes = [IsSuperUser]

class AdminProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsSuperUser]

class AdminAllocationViewSet(viewsets.ModelViewSet):
    queryset = Allocation.objects.all()
    serializer_class = AllocationSerializer
    permission_classes = [IsSuperUser]

class AdminSaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsSuperUser]

class AdminCustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsSuperUser]
