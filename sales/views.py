import csv
from django.http import HttpResponse
from rest_framework import viewsets, permissions, decorators, status
from rest_framework.response import Response
from .serializers import SaleSerializer, CustomerSerializer
from .models import Sale, Customer

class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
             return Customer.objects.none()
        return Customer.objects.filter(store__owner=self.request.user)

    def perform_create(self, serializer):
        # Allow passing store_id or pick first store if not provided
        # For simplicity, we assume one store per owner for now or store provided in data
        store_id = self.request.data.get('store')
        if not store_id:
             # Fallback to owner's first store
             from stores.models import Store
             store = Store.objects.filter(owner=self.request.user).first()
             serializer.save(store=store)
        else:
             serializer.save()

class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleSerializer
    queryset = Sale.objects.all()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
             return Sale.objects.none()
        # RBAC: Show sales for user's store
        return Sale.objects.filter(product__store__owner=self.request.user)

    @decorators.action(detail=False, methods=['GET'], url_path='export-csv')
    def export_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['IMEI', 'Brand', 'Model', 'Selling Price', 'Sale Price', 'Sold By', 'Customer', 'Date'])
        
        sales = self.get_queryset()
        for s in sales:
            writer.writerow([
                s.product.imei_number,
                s.product.brand,
                s.product.model_name,
                s.product.selling_price,
                s.sale_price,
                s.sold_by.email,
                s.customer_name,
                s.timestamp
            ])
        
        return response
