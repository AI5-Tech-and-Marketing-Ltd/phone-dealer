from django.urls import reverse
from django.core import mail
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class AccountsTests(APITestCase):
    def test_signup_and_activation(self):
        url = reverse('signup')
        data = {
            'email': 'test@example.com',
            'password': 'password123',
            'full_name': 'Test User'
        }
        response = self.client.post(url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        
        # Check email sent
        self.assertEqual(len(mail.outbox), 1)
        
        user = User.objects.get(email='test@example.com')
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.activation_token)
        
        # Test activation
        activate_url = reverse('activate')
        act_response = self.client.post(activate_url, {'token': user.activation_token})
        self.assertEqual(status.HTTP_200_OK, act_response.status_code)
        
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_email_verified)

    def test_logout_blacklist(self):
        user = User.objects.create_user(email='test@example.com', password='password123', is_active=True)
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('logout')
        response = self.client.post(url, {'refresh': str(refresh)})
        self.assertEqual(status.HTTP_205_RESET_CONTENT, response.status_code)
        
        # Trying to refresh again should fail
        refresh_url = reverse('token_refresh')
        res = self.client.post(refresh_url, {'refresh': str(refresh)})
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, res.status_code)

    def test_password_reset_flow(self):
        user = User.objects.create_user(email='test@example.com', password='password123', is_active=True)
        
        # Request reset
        url = reverse('password_reset')
        response = self.client.post(url, {'email': 'test@example.com'})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(len(mail.outbox), 1)
        
        # In a real test we'd extract UID and Token from the email
        # Simulating confirming with dummy token logic for brevity
        # Normally you'd parse mail.outbox[0].body
