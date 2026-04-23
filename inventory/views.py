from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
import csv
import os
import codecs
from django.conf import settings
from django.db import transaction, models
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, permissions, status, decorators, generics, parsers
from rest_framework.response import Response

from .serializers import (
    ProductSerializer, AllocationSerializer, 
    BulkSoldSerializer, ConditionSerializer, TacResponseSerializer,
    TacRecordSerializer, TacBulkSerializer, TacUploadResultSerializer
)
from .models import Product, Allocation, Condition, TacRecord
from .filters import ProductFilter
from .utils import fetch_imei_info
from .tac_utils import parse_csv_row, upsert_tac_records
from billing.permissions import HasActiveSubscription
from accounts.permissions import IsStoreOwner, IsStoreKeeper, IsSuperUser

# --- TAC Views ---

@extend_schema(tags=['Inventory'], responses=TacRecordSerializer(many=True))
class TacListView(generics.ListAPIView):
    """Paginated list of all TAC records from the database."""
    permission_classes = [IsSuperUser]
    serializer_class = TacRecordSerializer
    queryset = TacRecord.objects.all()
    # Search and Ordering are supported by default if filter backends are configured in settings
    # but let's be explicit if needed.

@extend_schema(tags=['Inventory'])
class TacCreateView(generics.CreateAPIView):
    """Create a single TAC record."""
    permission_classes = [IsSuperUser]
    serializer_class = TacRecordSerializer
    queryset = TacRecord.objects.all()

@extend_schema(tags=['Inventory'], request=TacBulkSerializer, responses=TacUploadResultSerializer)
class TacBulkCreateView(generics.GenericAPIView):
    """Bulk-create TAC records from a JSON payload."""
    permission_classes = [IsSuperUser]
    serializer_class = TacBulkSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = upsert_tac_records(serializer.validated_data['records'])
        return Response(result, status=status.HTTP_207_MULTI_STATUS)

@extend_schema(
    tags=['Inventory'],
    request={'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}}}},
    responses=TacUploadResultSerializer
)
class TacUploadView(generics.GenericAPIView):
    """
    Upload a CSV or .xlsx file to seed/update TAC records.
    Expected columns: tac, brand, name, contributor, comment, gsmarena_1, gsmarena_2, aka
    """
    permission_classes = [IsSuperUser]
    parser_classes = [parsers.MultiPartParser]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded.'}, status=status.HTTP_400_BAD_REQUEST)

        name = file.name.lower()
        try:
            if name.endswith('.csv'):
                records = self._parse_csv(file)
            elif name.endswith(('.xlsx', '.xls')):
                records = self._parse_excel(file)
            else:
                return Response({'error': 'Unsupported file type. Use .csv or .xlsx'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'File parsing failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        result = upsert_tac_records(records)
        return Response(result, status=status.HTTP_207_MULTI_STATUS)

    def _parse_csv(self, file):
        reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
        # Skip potential meta line if it looks like the Osmocom one
        first_line = next(reader, None)
        if first_line and "Osmocom" in first_line[0]:
             next(reader, None) # skip header too
        elif first_line and "tac" in first_line[0].lower():
             pass # it was the header, we already skipped it
        
        records = []
        for row in reader:
            r = parse_csv_row(row)
            if r:
                records.append(r)
        return records

    def _parse_excel(self, file):
        import openpyxl
        wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
        ws = wb.active
        rows = iter(ws.rows)
        header = next(rows, None) # skip header
        
        records = []
        for row in rows:
            values = [str(cell.value or '') for cell in row]
            r = parse_csv_row(values)
            if r:
                records.append(r)
        return records

@extend_schema(
    tags=['Inventory'],
    parameters=[OpenApiParameter('q', str, 'query', description='Search TAC code, brand, or model name')],
    responses=TacRecordSerializer(many=True)
)
class TacSearchView(generics.ListAPIView):
    """Search TAC records by TAC number, brand, or model name."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TacRecordSerializer

    def get_queryset(self):
        q = self.request.query_params.get('q', '').strip()
        if not q:
            return TacRecord.objects.none()
        return TacRecord.objects.filter(
            Q(tac__startswith=q) |
            Q(brand__icontains=q) |
            Q(name__icontains=q)
        )[:50]

# --- Existing Views ---

@extend_schema(tags=['Inventory'], examples=[OpenApiExample('Create Condition Example', value={'name': 'Slight Scratch', 'description': 'Minor cosmetic damage'}, request_only=True)])
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

@extend_schema(tags=['Inventory'], examples=[OpenApiExample('Create Product Example', value={'brand': 'Apple', 'model_name': 'iPhone 13', 'imei_number': '351234567890126', 'cost_price': 400000.0, 'selling_price': 550000.0, 'status': 'Available', 'availability': 'Public', 'condition_list': 'New, Factory Unlocked'}, request_only=True)])
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
        return Product.objects.filter(
            models.Q(store__owner=user) | models.Q(store=getattr(user, 'store', None))
        ).distinct()

    def perform_update(self, serializer):
        instance = serializer.instance
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

    @extend_schema(request=BulkSoldSerializer, examples=[OpenApiExample('Bulk Sold Example', value={'ids': [1, 2, 3], 'imeis': ['351234567890126']}, request_only=True)])
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
