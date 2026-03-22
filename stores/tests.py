from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Store, Subscription, Bill

User = get_user_model()

class StoresTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='password123', is_active=True)
        self.store = Store.objects.create(name='Test Store', owner=self.user)
        self.client.force_authenticate(user=self.user)

    def test_create_subscription_and_pay(self):
        url = reverse('subscribe')
        data = {'store_id': self.store.id, 'plan_type': 'Basic'}
        response = self.client.post(url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        
        bill_id = response.data['id']
        bill = Bill.objects.get(id=bill_id)
        self.assertEqual(bill.status, 'Pending')
        
        # Pay bill
        pay_url = reverse('pay-bill', kwargs={'pk': bill_id})
        res = self.client.post(pay_url)
        self.assertEqual(status.HTTP_200_OK, res.status_code)
        
        bill.refresh_from_db()
        self.assertEqual(bill.status, 'Paid')
        
        # Check sub created
        sub = Subscription.objects.get(store=self.store)
        self.assertEqual(sub.plan_type, 'Basic')

    def test_add_staff_billing(self):
        # Create active sub first
        Subscription.objects.create(
            store=self.store, plan_type='Basic', 
            expiry_date='2099-01-01', payment_status='Paid', max_staff=2
        )
        
        url = reverse('add-staff')
        response = self.client.post(url, {'store_id': self.store.id, 'count': 5})
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        
        bill_id = response.data['id']
        bill = Bill.objects.get(id=bill_id)
        self.assertEqual(bill.amount, 50.00) # 5 * 10
        
        # Pay it
        self.client.post(reverse('pay-bill', kwargs={'pk': bill_id}))
        
        # Check sub updated
        sub = Subscription.objects.get(store=self.store)
        self.assertEqual(sub.max_staff, 7) # 2 + 5
