from datetime import datetime, time, timedelta
from types import SimpleNamespace

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.devices.models import ConnectionSession, Device
from apps.devices.views import _day_ring_spans

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


class DeviceDetailOutageCountTests(TestCase):
    """The 'Power outages today' card still counts intra-day gaps."""

    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pw12345!")
        self.device = Device.objects.create(user=self.user, name="My device")
        self.client.force_login(self.user)

    def _add_session(self, start_time):
        ConnectionSession.objects.create(
            device=self.device, start_time=start_time, end_time=start_time
        )

    def _detail(self):
        return self.client.get(reverse("device_detail", kwargs={"pk": self.device.pk}))

    def test_counts_gaps_between_sessions(self):
        day = timezone.localtime().replace(hour=9, minute=0, second=0, microsecond=0)
        for hour in (9, 12, 15):
            self._add_session(day.replace(hour=hour))

        self.assertEqual(self._detail().context["today_outage_count"], 2)

    def test_is_zero_without_a_drop(self):
        day = timezone.localtime().replace(hour=9, minute=0, second=0, microsecond=0)
        self._add_session(day)

        self.assertEqual(self._detail().context["today_outage_count"], 0)


class DeviceDetailOfflineHoursTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pw12345!")
        self.device = Device.objects.create(user=self.user, name="My device")
        self.client.force_login(self.user)
        self.today = timezone.localtime().date()

    def _set_created_at(self, when):
        Device.objects.filter(pk=self.device.pk).update(created_at=when)
        self.device.refresh_from_db()

    def _add_session(self, start, end):
        ConnectionSession.objects.create(
            device=self.device, start_time=start, end_time=end
        )

    def _local(self, day, hour, minute=0):
        return timezone.make_aware(
            datetime.combine(day, time(hour, minute)),
            timezone.get_current_timezone(),
        )

    def _offline_hours(self, day):
        response = self.client.get(
            reverse("device_detail", kwargs={"pk": self.device.pk})
        )
        labels = response.context["daily_labels"]
        series = response.context["chart_data"]["daily"]["offlineHours"]
        return series[labels.index(day.strftime("%b %d"))]

    def test_full_day_offline_shows_24_hours(self):
        self._set_created_at(self._local(self.today - timedelta(days=2), 0))
        yesterday = self.today - timedelta(days=1)

        self.assertEqual(self._offline_hours(yesterday), 24.0)

    def test_partial_day_shows_remaining_offline_hours(self):
        self._set_created_at(self._local(self.today - timedelta(days=2), 0))
        yesterday = self.today - timedelta(days=1)
        self._add_session(self._local(yesterday, 9), self._local(yesterday, 15))

        self.assertAlmostEqual(self._offline_hours(yesterday), 18.0, places=2)

    def test_day_before_device_created_shows_zero(self):
        self._set_created_at(self._local(self.today, 0))
        before = self.today - timedelta(days=2)

        self.assertEqual(self._offline_hours(before), 0.0)

    def test_today_reports_offline_hours_so_far(self):
        self._set_created_at(self._local(self.today - timedelta(days=2), 0))
        self._add_session(self._local(self.today, 0), self._local(self.today, 1))

        elapsed = (timezone.localtime() - self._local(self.today, 0)).total_seconds()
        elapsed /= 3600

        self.assertAlmostEqual(self._offline_hours(self.today), elapsed - 1, delta=0.1)

    def test_session_crossing_midnight_is_clipped_to_the_day(self):
        self._set_created_at(self._local(self.today - timedelta(days=2), 0))
        yesterday = self.today - timedelta(days=1)
        self._add_session(self._local(yesterday, 23), self._local(self.today, 1))

        # Only the 23:00–24:00 hour belongs to yesterday.
        self.assertAlmostEqual(self._offline_hours(yesterday), 23.0, places=2)

    def test_page_labels_the_chart_as_offline_hours(self):
        response = self.client.get(
            reverse("device_detail", kwargs={"pk": self.device.pk})
        )

        self.assertContains(response, "Offline hours per day")
        self.assertNotContains(response, "Power outages per day")
        self.assertContains(response, "Power outages today")


class DeviceDetailTimelineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pw12345!")
        self.device = Device.objects.create(user=self.user, name="My device")
        self.client.force_login(self.user)

    def _add_session(self, start_time, end_time):
        ConnectionSession.objects.create(
            device=self.device, start_time=start_time, end_time=end_time
        )

    def _labels(self):
        response = self.client.get(
            reverse("device_detail", kwargs={"pk": self.device.pk})
        )
        return response.context["timeline_labels"]

    def test_completed_session_shows_start_and_end(self):
        start = (timezone.localtime() - timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        self._add_session(start, start.replace(hour=15, minute=20))

        self.assertEqual(self._labels(), [f"{start.strftime('%b %d, %H:%M')} → 15:20"])

    def test_ongoing_session_is_marked(self):
        now = timezone.now()
        self._add_session(now - timedelta(minutes=5), now)

        self.assertTrue(self._labels()[-1].endswith("→ ongoing"))

    def test_page_labels_the_timeline_card(self):
        response = self.client.get(
            reverse("device_detail", kwargs={"pk": self.device.pk})
        )

        self.assertContains(response, "Start → last ping")


class DayRingSpanTests(TestCase):
    """The 24-hour ring helper is pure: fixed times, no wall clock."""

    def setUp(self):
        tz = timezone.get_current_timezone()
        self.tz = tz
        self.day = timezone.localdate()
        self.day_start = self._at(0, 0)
        self.day_end = self.day_start + timedelta(days=1)

    def _at(self, hour, minute=0):
        return timezone.make_aware(
            datetime.combine(self.day, time(hour, minute)), self.tz
        )

    @staticmethod
    def _session(start, end):
        return SimpleNamespace(start_time=start, end_time=end)

    def _spans(self, monitored_start, monitored_end, sessions, has_data=True):
        return _day_ring_spans(
            self.day_start,
            self.day_end,
            monitored_start,
            monitored_end,
            sessions,
            has_data,
        )

    def test_unknown_edges_with_outage_around_a_session(self):
        spans = self._spans(
            self._at(6), self._at(18), [self._session(self._at(9), self._at(12))]
        )

        self.assertEqual(
            spans,
            [
                (self.day_start, self._at(6), "unknown"),
                (self._at(6), self._at(9), "outage"),
                (self._at(9), self._at(12), "online"),
                (self._at(12), self._at(18), "outage"),
                (self._at(18), self.day_end, "unknown"),
            ],
        )

    def test_session_crossing_midnight_is_clipped_to_the_day(self):
        spans = self._spans(
            self.day_start,
            self.day_end,
            [self._session(self._at(22) - timedelta(days=1), self._at(3))],
        )

        self.assertEqual(spans[0], (self.day_start, self._at(3), "online"))
        self.assertEqual(spans[-1], (self._at(3), self.day_end, "outage"))

    def test_touching_sessions_merge_into_one_online_span(self):
        spans = self._spans(
            self._at(9),
            self._at(11),
            [
                self._session(self._at(9), self._at(10)),
                self._session(self._at(10), self._at(11)),
            ],
        )

        self.assertIn((self._at(9), self._at(11), "online"), spans)
        self.assertEqual(
            [kind for _, _, kind in spans].count("online"), 1, spans
        )

    def test_no_recorded_data_is_unknown_not_outage(self):
        spans = self._spans(self.day_start, self._at(12), [], has_data=False)

        self.assertEqual(spans, [(self.day_start, self.day_end, "unknown")])


class DeviceDetailTodayRingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pw12345!")
        self.device = Device.objects.create(user=self.user, name="My device")
        self.client.force_login(self.user)
        self.today = timezone.localdate()

    def _set_created_at(self, when):
        Device.objects.filter(pk=self.device.pk).update(created_at=when)
        self.device.refresh_from_db()

    def _add_session(self, start, end):
        ConnectionSession.objects.create(
            device=self.device, start_time=start, end_time=end
        )

    def _local(self, day, hour, minute=0):
        return timezone.make_aware(
            datetime.combine(day, time(hour, minute)),
            timezone.get_current_timezone(),
        )

    def _segments(self):
        response = self.client.get(
            reverse("device_detail", kwargs={"pk": self.device.pk})
        )
        return response.context["chart_data"]["today"]["segments"]

    def test_ring_tiles_the_whole_day(self):
        self._set_created_at(self._local(self.today - timedelta(days=3), 0))
        self._add_session(self._local(self.today, 0), self._local(self.today, 1))

        total = sum(segment["minutes"] for segment in self._segments())

        self.assertAlmostEqual(total, 24 * 60, places=1)

    def test_the_rest_of_today_reads_as_unknown(self):
        self._set_created_at(self._local(self.today - timedelta(days=3), 0))

        segments = self._segments()

        self.assertEqual(segments[-1]["kind"], "unknown")
        self.assertEqual(segments[-1]["end"], "24:00")

    def test_session_today_reads_online_then_outage(self):
        self._set_created_at(self._local(self.today - timedelta(days=3), 0))
        self._add_session(self._local(self.today, 0), self._local(self.today, 1))

        segments = self._segments()

        self.assertEqual(segments[0]["kind"], "online")
        self.assertEqual(segments[0]["start"], "00:00")
        self.assertEqual(segments[1]["kind"], "outage")

    def test_device_without_any_session_is_not_all_outage(self):
        self._set_created_at(self._local(self.today - timedelta(days=3), 0))

        kinds = {segment["kind"] for segment in self._segments()}

        self.assertEqual(kinds, {"unknown"})

    def test_card_shows_the_ring_and_its_legend(self):
        response = self.client.get(
            reverse("device_detail", kwargs={"pk": self.device.pk})
        )

        self.assertContains(response, "24-hour ring")
        self.assertContains(response, "Outage")
        self.assertContains(response, "Remaining")
