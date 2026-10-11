from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.devices.models import Device

LOGIN_URL = "/accounts/login/"


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pw12345!")
        self.other = User.objects.create_user(username="other", password="pw12345!")
        self.device = Device.objects.create(user=self.user, name="My device")
        self.other_device = Device.objects.create(user=self.other, name="Their device")

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(LOGIN_URL))

    def test_lists_only_own_devices(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "My device")
        self.assertNotContains(response, "Their device")

    def test_add_device_creates_owned_device(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("dashboard"), {"action": "add", "name": "New device"}
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(
            Device.objects.filter(user=self.user, name="New device").exists()
        )

    def test_add_device_with_blank_name_does_not_create(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("dashboard"), {"action": "add", "name": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Device.objects.filter(user=self.user, name="").exists())

    def test_delete_removes_own_device(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("dashboard"),
            {"action": "delete", "device_id": str(self.device.pk)},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(Device.objects.filter(pk=self.device.pk).exists())

    def test_cannot_delete_another_users_device(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("dashboard"),
            {"action": "delete", "device_id": str(self.other_device.pk)},
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Device.objects.filter(pk=self.other_device.pk).exists())


class DeviceOnlineStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pw12345!")

    def test_recent_ping_is_online(self):
        device = Device.objects.create(
            user=self.user, name="Up", last_ping=timezone.now()
        )
        self.assertTrue(device.is_online)

    def test_stale_ping_is_offline(self):
        device = Device.objects.create(
            user=self.user,
            name="Down",
            last_ping=timezone.now() - timedelta(minutes=5),
        )
        self.assertFalse(device.is_online)


class ProfileRedirectTests(TestCase):
    def test_profile_redirects_to_dashboard(self):
        response = self.client.get("/accounts/profile/")
        self.assertRedirects(
            response, reverse("dashboard"), fetch_redirect_response=False
        )
