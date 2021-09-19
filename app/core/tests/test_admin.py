from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse


class AdminSiteTests(TestCase):
    def setUp(self) -> None:
        """A function that is ran before every test that is run.
         Sometimes there are setUp tasks that need to be run before every
         test in our TestCase class."""
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@pythonclass.com",
            password="test123"
        )
        self.client.force_login(self.admin_user)
        self.user = get_user_model().objects.create_user(
            email="user@pythonclass.com",
            password="test123",
            name="User Name Test"
        )

    def test_users_listed(self):
        """Test that users are listen correctly on user page"""
        url = reverse('admin:core_user_changelist')
        resp = self.client.get(url)

        self.assertContains(resp, self.user.name)
        self.assertContains(resp, self.user.email)
        self.assertContains(resp, self.admin_user.email)

    def test_user_change_page(self):
        """Test that User Edit page works"""
        url = reverse('admin:core_user_change', args=[self.user.id])
        # /admin/core/user/{user_id}
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)

    def test_create_user_page(self):
        """Test that the create user page works"""
        url = reverse('admin:core_user_add')
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
