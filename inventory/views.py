from drf_spectacular.utils import OpenApiExample
import csv
import os
from django.conf import settings
from rest_framework import viewsets, permissions, status, decorators, generics
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db import transaction, models
from django.utils import timezone
from .serializers import (
    ProductSerializer, AllocationSerializer, 
    BulkSoldSerializer, ConditionSerializer, TacResponseSerializer
)
from .models import Product, Allocation, Condition
from .filters import ProductFilter
from .utils import fetch_imei_info
from billing.permissions import HasActiveSubscription
from accounts.permissions import IsStoreOwner, IsStoreKeeper, IsSuperUser

@extend_schema(tags=['Inventory'], responses=TacResponseSerializer)
class TacListView(generics.GenericAPIView):
    """Paginated list of all TAC records from tacdb.csv."""
    permission_classes = [IsSuperUser]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='page', type=int, location='query', description='Page number (starting from 1)'),
            OpenApiParameter(name='page_size', type=int, location='query', description='Items per page (max 200)'),
        ]
    )
    def get(self, request):
        file_path = os.path.join(settings.BASE_DIR, 'tacdb.csv')
        if not os.path.exists(file_path):
             return Response({"error": "TAC database not found."}, status=404)

        try:
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 50)), 200)
            
            start_row = (page - 1) * page_size
            end_row = start_row + page_size
            
            data = []
            with open(file_path, mode='r', encoding='utf-8') as csvfile:
                # Skip first meta line
                next(csvfile)
                reader = csv.reader(csvfile)
                # Skip header
                header = next(reader)
                
                # Iterate and slice
                current_idx = 0
                for row in reader:
                    if current_idx >= start_row and current_idx < end_row:
                        # Index 7 is aka
                        aka_raw = row[7] if len(row) > 7 else ""
                        aka_list = [a.strip() for a in aka_raw.split(',')] if aka_raw else []
                        
                        data.append({
                            "tac": row[0] if len(row) > 0 else "",
                            "brand": row[1] if len(row) > 1 else "",
                            "name": row[2] if len(row) > 2 else "",
                            "aka": aka_list,
                            "contributor": row[3] if len(row) > 3 else "",
                            "comment": row[4] if len(row) > 4 else "",
                            "gsmarena_1": row[5] if len(row) > 5 else "",
                            "gsmarena_2": row[6] if len(row) > 6 else ""
                        })
                    current_idx += 1
                    if current_idx >= end_row:
                        break
            
            return Response({
                "page": page,
                "page_size": page_size,
                "total_records": 22529, # Hardcoded for speed
                "results": data
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)

@extend_schema(
    tags=['Inventory'],
    examples=[
        OpenApiExample(
            'Create Condition Example',
            value={'name': 'Slight Scratch', 'description': 'Minor cosmetic damage'},
            request_only=True
        )
    ]
)
class ConditionViewSet(viewsets.ModelViewSet):
    """Store specific device conditions."""
    serializer_class = ConditionSerializer
    queryset = Condition.objects.all()
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), (IsStoreOwner | IsStoreKeeper)(), HasActiveSubscription()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsStoreOwner(), HasActiveSubscription()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if getattr(self, 'swagger_fake_view', False):
             return Condition.objects.none()
        if user.role == 'SuperUser':
            return Condition.objects.all()
        return Condition.objects.filter(
            models.Q(store__owner=user) | models.Q(store=getattr(user, 'store', None))
        ).distinct()

@extend_schema(
    tags=['Inventory'],
    examples=[
        OpenApiExample(
            'Create Product Example',
            value={
                'brand': 'Apple',
                'model_name': 'iPhone 13',
                'imei_number': '351234567890126',
                'cost_price': 400000.0,
                'selling_price': 550000.0,
                'status': 'Available',
                'availability': 'Public',
                'condition_list': 'New, Factory Unlocked'
            },
            request_only=True
        )
    ]
)
class ProductViewSet(viewsets.ModelViewSet):
    """Internal inventory management for store staff."""
    serializer_class = ProductSerializer
    queryset = Product.objects.all()
    filterset_class = ProductFilter

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), (IsStoreOwner | IsStoreKeeper)(), HasActiveSubscription()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsStoreOwner(), HasActiveSubscription()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if getattr(self, 'swagger_fake_view', False):
             return Product.objects.none()
        if user.role == 'SuperUser':
            return Product.objects.all()
        # Staff (Owner or Keeper) can see all their store's products (Private/Public)
        return Product.objects.filter(
            models.Q(store__owner=user) | models.Q(store=getattr(user, 'store', None))
        ).distinct()

    def perform_update(self, serializer):
        instance = serializer.instance
        # Only check status if it's in validated_data
        status_val = serializer.validated_data.get('status')
        if status_val == 'Sold' and instance.status != 'Sold':
            serializer.save(sold_at=timezone.now())
        elif status_val and status_val != 'Sold':
            serializer.save(sold_at=None)
        else:
            serializer.save()

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

    @extend_schema(
        request=BulkSoldSerializer,
        examples=[
            OpenApiExample(
                'Bulk Sold Example',
                value={'ids': [1, 2, 3], 'imeis': ['351234567890126']},
                request_only=True
            )
        ]
    )
    @decorators.action(detail=False, methods=['POST'], url_path='bulk-sold', permission_classes=[HasActiveSubscription])
    @transaction.atomic
    def bulk_sold(self, request):
        serializer = BulkSoldSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ids = serializer.validated_data.get('ids', [])
        imeis = serializer.validated_data.get('imeis', [])
        
        updated_count = Product.objects.filter(
            models.Q(id__in=ids) | models.Q(imei_number__in=imeis)
        ).update(status='Sold', sold_at=timezone.now())
        
        return Response({"message": f"Successfully updated {updated_count} products."}, status=status.HTTP_200_OK)


@extend_schema(tags=['Inventory'])
class AllocationViewSet(viewsets.ModelViewSet):
    serializer_class = AllocationSerializer
    queryset = Allocation.objects.all()
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [permissions.IsAuthenticated(), (IsStoreOwner | IsStoreKeeper)(), HasActiveSubscription()]
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), IsStoreOwner(), HasActiveSubscription()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if getattr(self, 'swagger_fake_view', False):
             return Allocation.objects.none()
        return Allocation.objects.filter(
            models.Q(store__owner=user) | models.Q(store=getattr(user, 'store', None))
        ).distinct()
