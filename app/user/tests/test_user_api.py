from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """Test user API unauthenticated (public)"""
    def setUp(self) -> None:
        self.client = APIClient()

    def test_create_valid_user_success(self):
        """Test creating user with valid payload is successful"""
        payload = {
            'email': 'test@pythonapp.com',
            'password': 'password',
            'name': 'Test Name'
        }
        resp = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        user = get_user_model().objects.get(**resp.data)
        self.assertTrue(user.check_password(payload['password']))

        self.assertNotIn('password', resp.data)

    def test_user_exists(self):
        """Test creating a user that already exists fails"""
        payload = {
            'email': 'test@pythonapp.com',
            'password': 'password',
            'name': 'Test Name'
        }

        create_user(**payload)
        resp = self.client.post(CREATE_USER_URL, payload)
        self.assertTrue(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self):
        """Test that the password must be more than 5 chars"""
        payload = {
            'email': 'test@pythonapp.com',
            'password': 'pass',
            'name': 'Test Name'
        }

        resp = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=payload['email']).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """Test that a token is created for the user"""
        payload = {'email': 'python@pythonapp.com', 'password': 'test123'}
        create_user(**payload)
        resp = self.client.post(TOKEN_URL, payload)
        self.assertIn('token', resp.data)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_create_token_invalid_credentials(self):
        """Test that token is not create if invalid credentials are provided"""
        create_user(email="python@pythonapp.com", password="test123")
        payload = {'email': 'python@pythonapp.com', 'password': 'wrongpass'}
        resp = self.client.post(TOKEN_URL, payload)
        self.assertNotIn('token', resp.data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_no_user(self):
        """Test that token is not created if user doesn't exist"""
        payload = {'email': 'python@pythonapp.com', 'password': 'testpass'}
        resp = self.client.post(TOKEN_URL, payload)
        self.assertNotIn('token', resp.data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_missing_field(self):
        """Test that email and password are required"""
        resp = self.client.post(TOKEN_URL, {'email': 'email',
                                            'password': 'pass'})
        self.assertNotIn('token', resp.data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        """Test that authentication is required for users"""
        resp = self.client.get(ME_URL)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserAPITests(TestCase):
    """Test API requests that require authentication"""
    def setUp(self) -> None:
        self.user = create_user(email='test@pythonapp.com',
                                password='password1',
                                name="Test User")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_success(self):
        """Test retrieving profile for logged in user"""
        resp = self.client.get(ME_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, {'name': 'Test User',
                                     'email': 'test@pythonapp.com'})

    def test_post_me_not_allowed(self):
        """Test that POST is not allowed on ME_URL"""
        resp = self.client.post(ME_URL, {})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """Test updating the user profile for authenticated user"""
        payload = {'name': 'New Name', 'password': 'newpassword'}
        resp = self.client.patch(ME_URL, payload)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
