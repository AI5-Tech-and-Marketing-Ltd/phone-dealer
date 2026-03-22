from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from stores.models import Store
from inventory.models import Product
from .models import Customer, Sale

User = get_user_model()

class SalesAndInventoryTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='password123', is_active=True)
        self.store = Store.objects.create(name='Test Store', owner=self.user)
        self.client.force_authenticate(user=self.user)

    def test_customer_crud(self):
        url = reverse('customer-list') # Registered in router
        data = {'full_name': 'John Doe', 'phone': '123456789'}
        response = self.client.post(url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        
        cust_id = response.data['id']
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(Customer.objects.get(id=cust_id).store, self.store)

    def test_inventory_cloudinary_signature(self):
        url = reverse('cloudinary-signature')
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertIn('signature', response.data)

    def test_marketplace_public_endpoints(self):
        # Public, no auth
        self.client.force_authenticate(user=None)
        
        # Test store list
        url = reverse('store-list')
        response = self.client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        
        # Test product list
        product_url = reverse('marketplace-list')
        response = self.client.get(product_url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_set_image_url(self):
        p = Product.objects.create(
            brand='Samsung', model_name='S21', imei_number='357951123456789', 
            cost_price=500, selling_price=700, store=self.store
        )
        url = reverse('set-image-url')
        data = {'type': 'product', 'id': p.id, 'url': 'test_image_url'}
        response = self.client.post(url, data)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        
        p.refresh_from_db()
        self.assertIn('test_image_url', str(p.image))
