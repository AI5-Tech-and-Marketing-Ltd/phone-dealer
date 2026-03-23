from rest_framework import viewsets, permissions, status, decorators
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db import transaction, models
from .serializers import ProductSerializer, AllocationSerializer, BulkSoldSerializer
from .models import Product, Allocation
from .filters import ProductFilter
from .utils import fetch_imei_info

@extend_schema(tags=['Inventory'])
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()
    filterset_class = ProductFilter

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            from accounts.permissions import IsStoreOwner, IsSuperUser
            return [(IsStoreOwner | IsSuperUser)()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
             return Product.objects.none()
        # RBAC: filtering by store ownership if not superuser
        if self.request.user.role == 'SuperUser':
            return Product.objects.all()
        return Product.objects.filter(store__owner=self.request.user)

    @extend_schema(description="Lookup device information by IMEI")
    @decorators.action(detail=False, methods=['GET'], url_path='imei-lookup/(?P<imei>[0-9]+)')
    def imei_lookup(self, request, imei=None):
        info = fetch_imei_info(imei)
        try:
            p = Product.objects.get(imei_number=imei)
            info['product'] = ProductSerializer(p).data
        except Product.DoesNotExist:
             info['product'] = None
        return Response(info)

    @extend_schema(request=BulkSoldSerializer)
    @decorators.action(detail=False, methods=['POST'], url_path='bulk-sold')
    @transaction.atomic
    def bulk_sold(self, request):
        serializer = BulkSoldSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ids = serializer.validated_data.get('ids', [])
        imeis = serializer.validated_data.get('imeis', [])
        
        updated_count = Product.objects.filter(
            models.Q(id__in=ids) | models.Q(imei_number__in=imeis)
        ).update(status='Sold')
        
        return Response({"message": f"Successfully updated {updated_count} products."}, status=status.HTTP_200_OK)

@extend_schema(tags=['Inventory'])
class AllocationViewSet(viewsets.ModelViewSet):
    serializer_class = AllocationSerializer
    queryset = Allocation.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
             return Allocation.objects.none()
        return Allocation.objects.filter(store__owner=self.request.user)
