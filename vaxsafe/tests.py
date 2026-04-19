"""
VaxSafe — 100+ Unit Test Suite
================================
Run with:
    python manage.py test vaxsafe.tests
    python manage.py test vaxsafe.tests --verbosity=2

App label adjust korte hobe jodi vaxsafe_app use koro:
    python manage.py test vaxsafe_app.tests

Coverage:
----------
1.  Profile Model
2.  FamilyMember Model
3.  Vaccine Model
4.  Reminder Model
5.  VaccinationCenter Model
6.  News Model
7.  VaccineUpdate Model
8.  VaccineReminder Model
9.  Notification Model
10. VaccineSchedule Model
11. CustomVaccineType Model
12. OTPVerification Model
13. FamilyGroup & FamilyGroupMember Models
14. FamilyInvitation Model
15. Update Model
"""

from datetime import date, time, timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone


# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def make_user(username="testuser", password="StrongPass123!", email=None):
    return User.objects.create_user(
        username=username,
        password=password,
        email=email or f"{username}@example.com",
        first_name="Test",
        last_name="User",
    )


def make_admin(username="adminuser", password="AdminPass123!"):
    return User.objects.create_user(
        username=username,
        password="AdminPass123!",
        email=f"{username}@example.com",
        is_staff=True,
    )


# ═══════════════════════════════════════════════
# 1. UPDATE MODEL TESTS
# ═══════════════════════════════════════════════

class UpdateModelTest(TestCase):

    def setUp(self):
        self.user = make_user()

    # Test 1
    def test_create_update(self):
        from vaxsafe.models import Update
        u = Update.objects.create(title="New Policy", posted_by=self.user)
        self.assertEqual(u.title, "New Policy")

    # Test 2
    def test_update_str(self):
        from vaxsafe.models import Update
        u = Update.objects.create(title="Flu Season Alert")
        self.assertEqual(str(u), "Flu Season Alert")

    # Test 3
    def test_update_created_at_auto(self):
        from vaxsafe.models import Update
        u = Update.objects.create(title="Test Update")
        self.assertIsNotNone(u.created_at)

    # Test 4
    def test_update_posted_by_can_be_null(self):
        from vaxsafe.models import Update
        u = Update.objects.create(title="Anonymous Update", posted_by=None)
        self.assertIsNone(u.posted_by)

    # Test 5
    def test_update_ordering_latest_first(self):
        from vaxsafe.models import Update
        u1 = Update.objects.create(title="First")
        u2 = Update.objects.create(title="Second")
        updates = list(Update.objects.all())
        self.assertEqual(updates[0], u2)  # latest first


# ═══════════════════════════════════════════════
# 2. PROFILE MODEL TESTS
# ═══════════════════════════════════════════════

class ProfileModelTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def _get_or_create_profile(self):
        from vaxsafe.models import Profile
        profile, _ = Profile.objects.get_or_create(user=self.user)
        return profile

    # Test 6
    def test_profile_str(self):
        profile = self._get_or_create_profile()
        self.assertIn(self.user.username, str(profile))

    # Test 7
    def test_profile_get_full_name_with_name(self):
        profile = self._get_or_create_profile()
        self.assertIn("Test", profile.get_full_name())

    # Test 8
    def test_profile_get_full_name_fallback_username(self):
        user2 = make_user(username="noname2")
        user2.first_name = ""
        user2.last_name = ""
        user2.save()
        from vaxsafe.models import Profile
        profile, _ = Profile.objects.get_or_create(user=user2)
        self.assertEqual(profile.get_full_name(), "noname2")

    # Test 9
    def test_profile_optional_fields_null_by_default(self):
        profile = self._get_or_create_profile()
        self.assertIsNone(profile.mobile)
        self.assertIsNone(profile.gender)

    # Test 10
    def test_profile_mobile_can_be_set(self):
        profile = self._get_or_create_profile()
        profile.mobile = "01712345678"
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.mobile, "01712345678")

    # Test 11
    def test_profile_gender_choices(self):
        profile = self._get_or_create_profile()
        for gender in ("Male", "Female", "Other"):
            profile.gender = gender
            profile.save()
            profile.refresh_from_db()
            self.assertEqual(profile.gender, gender)

    # Test 12
    def test_profile_blood_group_field(self):
        profile = self._get_or_create_profile()
        profile.blood_group = "O+"
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.blood_group, "O+")


# ═══════════════════════════════════════════════
# 3. FAMILY MEMBER MODEL TESTS
# ═══════════════════════════════════════════════

class FamilyMemberModelTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def _make_member(self, name="Alice", age=10, relation="Child", dob=None):
        from vaxsafe.models import FamilyMember
        return FamilyMember.objects.create(
            user=self.user,
            name=name,
            age=age,
            relation=relation,
            date_of_birth=dob,
        )

    # Test 13
    def test_create_family_member(self):
        m = self._make_member()
        self.assertEqual(m.name, "Alice")

    # Test 14
    def test_family_member_str(self):
        m = self._make_member()
        self.assertIn("Alice", str(m))
        self.assertIn("Child", str(m))

    # Test 15
    def test_family_member_belongs_to_user(self):
        from vaxsafe.models import FamilyMember
        self._make_member()
        self.assertEqual(FamilyMember.objects.filter(user=self.user).count(), 1)

    # Test 16
    def test_calculate_age_with_dob(self):
        dob = date.today() - timedelta(days=365 * 8)
        m = self._make_member(dob=dob)
        calculated = m.calculate_age()
        self.assertIn(calculated, [7, 8])

    # Test 17
    def test_calculate_age_falls_back_to_age_field(self):
        m = self._make_member(age=12)
        self.assertEqual(m.calculate_age(), 12)

    # Test 18
    def test_display_age_property(self):
        m = self._make_member(age=5)
        self.assertIn(str(m.display_age), ["5", "N/A"] + [str(i) for i in range(1, 20)])

    # Test 19
    def test_all_relationship_choices(self):
        from vaxsafe.models import FamilyMember
        for rel in ("Self", "Spouse", "Child", "Parent", "Sibling", "Grandparent", "Grandchild", "Other"):
            m = FamilyMember.objects.create(user=self.user, name=f"Person_{rel}", relation=rel)
            self.assertEqual(m.relation, rel)

    # Test 20
    def test_family_member_ordering_by_name(self):
        from vaxsafe.models import FamilyMember
        self._make_member(name="Zara")
        self._make_member(name="Alice2")
        names = list(FamilyMember.objects.filter(user=self.user).values_list("name", flat=True))
        self.assertEqual(names, sorted(names))

    # Test 21
    def test_family_member_created_at_auto(self):
        m = self._make_member()
        self.assertIsNotNone(m.created_at)

    # Test 22
    def test_family_member_notification_type_choices(self):
        from vaxsafe.models import FamilyMember
        for nt in ("Email", "SMS", "App Notification"):
            m = FamilyMember.objects.create(
                user=self.user, name=f"P_{nt}", relation="Child", notification_type=nt
            )
            self.assertEqual(m.notification_type, nt)


# ═══════════════════════════════════════════════
# 4. VACCINE MODEL TESTS
# ═══════════════════════════════════════════════

class VaccineModelTest(TestCase):

    def setUp(self):
        self.user = make_user()
        from vaxsafe.models import FamilyMember
        self.member = FamilyMember.objects.create(
            user=self.user, name="Bob", relation="Child"
        )

    def _make_vaccine(self, name="COVID-19", status="Completed", member=None):
        from vaxsafe.models import Vaccine
        return Vaccine.objects.create(
            user=self.user,
            family_member=member,
            name=name,
            dose_number="1st",
            date_administered=date.today(),
            status=status,
        )

    # Test 23
    def test_create_vaccine(self):
        v = self._make_vaccine()
        self.assertEqual(v.name, "COVID-19")

    # Test 24
    def test_vaccine_str_with_family_member(self):
        v = self._make_vaccine(member=self.member)
        self.assertIn("Bob", str(v))

    # Test 25
    def test_vaccine_str_without_family_member(self):
        v = self._make_vaccine()
        self.assertIn("Test User", str(v))

    # Test 26
    def test_get_recipient_name_family_member(self):
        v = self._make_vaccine(member=self.member)
        self.assertEqual(v.get_recipient_name(), "Bob")

    # Test 27
    def test_get_recipient_name_self(self):
        v = self._make_vaccine()
        self.assertIn("Test", v.get_recipient_name())

    # Test 28
    def test_is_upcoming_future_date(self):
        from vaxsafe.models import Vaccine
        v = Vaccine.objects.create(
            user=self.user, name="MMR", dose_number="1st",
            date_administered=date.today() + timedelta(days=5), status="Scheduled"
        )
        self.assertTrue(v.is_upcoming())

    # Test 29
    def test_is_upcoming_past_date(self):
        from vaxsafe.models import Vaccine
        v = Vaccine.objects.create(
            user=self.user, name="BCG", dose_number="1st",
            date_administered=date.today() - timedelta(days=5), status="Completed"
        )
        self.assertFalse(v.is_upcoming())

    # Test 30
    def test_is_overdue(self):
        from vaxsafe.models import Vaccine
        v = Vaccine.objects.create(
            user=self.user, name="Polio", dose_number="2nd",
            date_administered=date.today() - timedelta(days=3), status="Scheduled"
        )
        self.assertTrue(v.is_overdue())

    # Test 31
    def test_is_not_overdue_when_completed(self):
        from vaxsafe.models import Vaccine
        v = Vaccine.objects.create(
            user=self.user, name="Typhoid", dose_number="1st",
            date_administered=date.today() - timedelta(days=3), status="Completed"
        )
        self.assertFalse(v.is_overdue())

    # Test 32
    def test_days_until_future(self):
        from vaxsafe.models import Vaccine
        future = date.today() + timedelta(days=10)
        v = Vaccine.objects.create(
            user=self.user, name="HPV", dose_number="1st",
            date_administered=future, status="Scheduled"
        )
        self.assertEqual(v.days_until(), 10)

    # Test 33
    def test_vaccine_status_choices(self):
        for status in ("Scheduled", "Completed", "Overdue", "Cancelled"):
            v = self._make_vaccine(status=status)
            self.assertEqual(v.status, status)

    # Test 34
    def test_vaccine_next_dose_date_nullable(self):
        v = self._make_vaccine()
        self.assertIsNone(v.next_dose_date)

    # Test 35
    def test_vaccine_next_dose_date_can_be_set(self):
        from vaxsafe.models import Vaccine
        future = date.today() + timedelta(days=30)
        v = Vaccine.objects.create(
            user=self.user, name="Hepatitis B", dose_number="1st",
            date_administered=date.today(), status="Completed",
            next_dose_date=future
        )
        self.assertEqual(v.next_dose_date, future)

    # Test 36
    def test_vaccine_ordering_latest_first(self):
        from vaxsafe.models import Vaccine
        Vaccine.objects.create(user=self.user, name="BCG", dose_number="1st",
                               date_administered=date.today() - timedelta(days=10), status="Completed")
        Vaccine.objects.create(user=self.user, name="MMR", dose_number="1st",
                               date_administered=date.today(), status="Completed")
        vaccines = list(Vaccine.objects.filter(user=self.user))
        self.assertGreaterEqual(vaccines[0].date_administered, vaccines[1].date_administered)


# ═══════════════════════════════════════════════
# 5. REMINDER MODEL TESTS
# ═══════════════════════════════════════════════

class ReminderModelTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def _make_reminder(self, days_ahead=5, completed=False):
        from vaxsafe.models import Reminder
        return Reminder.objects.create(
            user=self.user,
            vaccine_name="COVID-19",
            scheduled_datetime=timezone.now() + timedelta(days=days_ahead),
            family_member="Alice",
            completed=completed,
        )

    # Test 37
    def test_create_reminder(self):
        r = self._make_reminder()
        self.assertEqual(r.vaccine_name, "COVID-19")

    # Test 38
    def test_reminder_str(self):
        r = self._make_reminder()
        self.assertIn("COVID-19", str(r))
        self.assertIn("Alice", str(r))

    # Test 39
    def test_status_active(self):
        r = self._make_reminder(days_ahead=3)
        self.assertEqual(r.status, "Active")

    # Test 40
    def test_status_completed(self):
        r = self._make_reminder(completed=True)
        self.assertEqual(r.status, "Completed")

    # Test 41
    def test_status_missed(self):
        from vaxsafe.models import Reminder
        r = Reminder.objects.create(
            user=self.user,
            vaccine_name="BCG",
            scheduled_datetime=timezone.now() - timedelta(days=2),
            family_member="Bob",
            completed=False,
        )
        self.assertEqual(r.status, "Missed")

    # Test 42
    def test_is_active_property(self):
        r = self._make_reminder(days_ahead=5)
        self.assertTrue(r.is_active)

    # Test 43
    def test_is_missed_property(self):
        from vaxsafe.models import Reminder
        r = Reminder.objects.create(
            user=self.user,
            vaccine_name="MMR",
            scheduled_datetime=timezone.now() - timedelta(hours=1),
            family_member="Charlie",
            completed=False,
        )
        self.assertTrue(r.is_missed)

    # Test 44
    def test_time_until_completed(self):
        r = self._make_reminder(completed=True)
        self.assertEqual(r.time_until(), "Completed")

    # Test 45
    def test_time_until_days(self):
        r = self._make_reminder(days_ahead=5)
        result = r.time_until()
        self.assertIn("day", result)

    # Test 46
    def test_reminder_created_at(self):
        r = self._make_reminder()
        self.assertIsNotNone(r.created_at)


# ═══════════════════════════════════════════════
# 6. VACCINATION CENTER MODEL TESTS
# ═══════════════════════════════════════════════

class VaccinationCenterModelTest(TestCase):

    def _make_center(self, name="City Clinic", city="Dhaka", lat=23.81, lng=90.41):
        from vaxsafe.models import VaccinationCenter
        return VaccinationCenter.objects.create(
            name=name,
            address="123 Main St",
            city=city,
            opening_time=time(8, 0),
            closing_time=time(20, 0),
            is_verified=True,
            is_active=True,
            rating=4.5,
            latitude=lat,
            longitude=lng,
            available_vaccines="COVID-19,Influenza,BCG",
        )

    # Test 47
    def test_create_center(self):
        c = self._make_center()
        self.assertEqual(c.name, "City Clinic")

    # Test 48
    def test_center_str(self):
        c = self._make_center()
        self.assertIn("City Clinic", str(c))
        self.assertIn("Dhaka", str(c))

    # Test 49
    def test_get_operating_hours(self):
        c = self._make_center()
        hours = c.get_operating_hours()
        self.assertIn("AM", hours)
        self.assertIn("PM", hours)

    # Test 50
    def test_get_operating_hours_not_specified(self):
        from vaxsafe.models import VaccinationCenter
        c = VaccinationCenter.objects.create(name="Unknown Clinic", address="X", city="Sylhet")
        self.assertEqual(c.get_operating_hours(), "Not specified")

    # Test 51
    def test_get_vaccines_list(self):
        c = self._make_center()
        vaccines = c.get_vaccines_list()
        self.assertIn("COVID-19", vaccines)
        self.assertIn("BCG", vaccines)
        self.assertEqual(len(vaccines), 3)

    # Test 52
    def test_get_vaccines_list_empty(self):
        from vaxsafe.models import VaccinationCenter
        c = VaccinationCenter.objects.create(
            name="Empty Center", address="Nowhere", city="Rangpur",
            available_vaccines=""
        )
        self.assertEqual(c.get_vaccines_list(), [])

    # Test 53
    def test_get_google_maps_url(self):
        c = self._make_center()
        url = c.get_google_maps_url()
        self.assertIn("google.com/maps", url)

    # Test 54
    def test_get_google_maps_url_no_coords(self):
        from vaxsafe.models import VaccinationCenter
        c = VaccinationCenter.objects.create(name="No GPS", address="X", city="Khulna")
        self.assertEqual(c.get_google_maps_url(), "#")

    # Test 55
    def test_get_distance_from(self):
        c = self._make_center(lat=23.81, lng=90.41)
        dist = c.get_distance_from(23.80, 90.40)
        self.assertIsInstance(dist, float)
        self.assertGreater(dist, 0)

    # Test 56
    def test_get_distance_returns_none_without_coords(self):
        from vaxsafe.models import VaccinationCenter
        c = VaccinationCenter.objects.create(name="No Coord", address="Y", city="Barisal")
        result = c.get_distance_from(23.0, 90.0)
        self.assertIsNone(result)

    # Test 57
    def test_is_verified_field(self):
        c = self._make_center()
        self.assertTrue(c.is_verified)

    # Test 58
    def test_rating_field(self):
        c = self._make_center()
        self.assertEqual(float(c.rating), 4.5)


# ═══════════════════════════════════════════════
# 7. NEWS MODEL TESTS
# ═══════════════════════════════════════════════

class NewsModelTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def _make_news(self, title="Test News", category="General"):
        from vaxsafe.models import News
        return News.objects.create(
            title=title,
            category=category,
            summary="A brief summary.",
            content="Full content of the news article here.",
            author=self.user,
        )

    # Test 59
    def test_create_news(self):
        n = self._make_news()
        self.assertEqual(n.title, "Test News")

    # Test 60
    def test_news_str(self):
        n = self._make_news()
        self.assertEqual(str(n), "Test News")

    # Test 61
    def test_news_auto_slug_generated(self):
        n = self._make_news(title="Auto Slug Test")
        self.assertIsNotNone(n.slug)
        self.assertIn("auto-slug-test", n.slug)

    # Test 62
    def test_news_slug_unique_on_duplicate_title(self):
        from vaxsafe.models import News
        n1 = self._make_news(title="Duplicate Title")
        n2 = News.objects.create(
            title="Duplicate Title", summary="S", content="C"
        )
        self.assertNotEqual(n1.slug, n2.slug)

    # Test 63
    def test_news_increment_views(self):
        n = self._make_news()
        initial = n.views
        n.increment_views()
        n.refresh_from_db()
        self.assertEqual(n.views, initial + 1)

    # Test 64
    def test_news_get_reading_time(self):
        n = self._make_news()
        result = n.get_reading_time()
        self.assertIn("min read", result)

    # Test 65
    def test_news_is_published_default_true(self):
        n = self._make_news()
        self.assertTrue(n.is_published)

    # Test 66
    def test_news_is_featured_default_false(self):
        n = self._make_news()
        self.assertFalse(n.is_featured)

    # Test 67
    def test_news_category_choices(self):
        for cat in ("General", "COVID-19", "Vaccines", "Research", "Policy", "Awareness", "Alert"):
            n = self._make_news(title=f"News {cat}", category=cat)
            self.assertEqual(n.category, cat)


# ═══════════════════════════════════════════════
# 8. VACCINE UPDATE MODEL TESTS
# ═══════════════════════════════════════════════

class VaccineUpdateModelTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def _make_update(self, title="Booster Campaign", category="campaign"):
        from vaxsafe.models import VaccineUpdate
        return VaccineUpdate.objects.create(
            title=title,
            content="Full content here.",
            category=category,
            author=self.user,
        )

    # Test 68
    def test_create_vaccine_update(self):
        u = self._make_update()
        self.assertEqual(u.title, "Booster Campaign")

    # Test 69
    def test_vaccine_update_str(self):
        u = self._make_update()
        self.assertIn("Booster Campaign", str(u))

    # Test 70
    def test_vaccine_update_created_at(self):
        u = self._make_update()
        self.assertIsNotNone(u.created_at)

    # Test 71
    def test_vaccine_update_is_published_default(self):
        u = self._make_update()
        self.assertTrue(u.is_published)

    # Test 72
    def test_vaccine_update_category_choices(self):
        for cat in ("general", "campaign", "new_vaccine", "policy", "alert", "schedule"):
            u = self._make_update(title=f"Update {cat}", category=cat)
            self.assertEqual(u.category, cat)


# ═══════════════════════════════════════════════
# 9. VACCINE REMINDER MODEL TESTS
# ═══════════════════════════════════════════════

class VaccineReminderModelTest(TestCase):

    def setUp(self):
        self.user = make_user()
        from vaxsafe.models import FamilyMember
        self.member = FamilyMember.objects.create(
            user=self.user, name="Riya", relation="Child"
        )

    def _make_reminder(self, days_ahead=5, member=None):
        from vaxsafe.models import VaccineReminder
        return VaccineReminder.objects.create(
            user=self.user,
            vaccine_name="MMR",
            reminder_date=date.today() + timedelta(days=days_ahead),
            reminder_time=time(9, 0),
            family_member=member,
        )

    # Test 73
    def test_create_vaccine_reminder(self):
        r = self._make_reminder()
        self.assertEqual(r.vaccine_name, "MMR")

    # Test 74
    def test_vaccine_reminder_str_self(self):
        r = self._make_reminder()
        self.assertIn("Self", str(r))

    # Test 75
    def test_vaccine_reminder_str_with_member(self):
        r = self._make_reminder(member=self.member)
        self.assertIn("Riya", str(r))

    # Test 76
    def test_get_recipient_name_self(self):
        r = self._make_reminder()
        name = r.get_recipient_name()
        self.assertIn("Test", name)

    # Test 77
    def test_get_recipient_name_family_member(self):
        r = self._make_reminder(member=self.member)
        self.assertEqual(r.get_recipient_name(), "Riya")

    # Test 78
    def test_is_sent_default_false(self):
        r = self._make_reminder()
        self.assertFalse(r.is_sent)

    # Test 79
    def test_past_reminder_date(self):
        from vaxsafe.models import VaccineReminder
        r = VaccineReminder.objects.create(
            user=self.user,
            vaccine_name="BCG",
            reminder_date=date.today() - timedelta(days=3),
            reminder_time=time(9, 0),
        )
        self.assertLess(r.reminder_date, date.today())


# ═══════════════════════════════════════════════
# 10. NOTIFICATION MODEL TESTS
# ═══════════════════════════════════════════════

class NotificationModelTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def _make_notif(self, notif_type="reminder"):
        from vaxsafe.models import Notification
        return Notification.objects.create(
            user=self.user,
            title="Vaccine Due",
            message="Your dose is scheduled.",
            notif_type=notif_type,
        )

    # Test 80
    def test_create_notification(self):
        n = self._make_notif()
        self.assertEqual(n.title, "Vaccine Due")

    # Test 81
    def test_notification_str(self):
        n = self._make_notif()
        self.assertIn("Vaccine Due", str(n))
        self.assertIn(self.user.username, str(n))

    # Test 82
    def test_is_read_default_false(self):
        n = self._make_notif()
        self.assertFalse(n.is_read)

    # Test 83
    def test_mark_as_read(self):
        n = self._make_notif()
        n.is_read = True
        n.save()
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    # Test 84
    def test_notif_type_choices(self):
        for t in ("reminder", "update", "alert"):
            n = self._make_notif(notif_type=t)
            self.assertEqual(n.notif_type, t)

    # Test 85
    def test_notification_created_at(self):
        n = self._make_notif()
        self.assertIsNotNone(n.created_at)

    # Test 86
    def test_notification_ordering_latest_first(self):
        from vaxsafe.models import Notification
        n1 = self._make_notif()
        n2 = self._make_notif()
        notifs = list(Notification.objects.filter(user=self.user))
        self.assertEqual(notifs[0], n2)


# ═══════════════════════════════════════════════
# 11. OTP VERIFICATION MODEL TESTS
# ═══════════════════════════════════════════════

class OTPVerificationModelTest(TestCase):

    def _make_otp(self, email="test@example.com", otp="123456", used=False, attempts=0):
        from vaxsafe.models import OTPVerification
        return OTPVerification.objects.create(
            email=email,
            otp=otp,
            full_name="Test User",
            hashed_password="hashed_pwd_here",
            is_used=used,
            attempts=attempts,
        )

    # Test 87
    def test_create_otp(self):
        otp = self._make_otp()
        self.assertEqual(otp.otp, "123456")

    # Test 88
    def test_otp_str(self):
        otp = self._make_otp()
        self.assertIn("123456", str(otp))
        self.assertIn("test@example.com", str(otp))

    # Test 89
    def test_otp_is_valid_fresh(self):
        otp = self._make_otp()
        self.assertTrue(otp.is_valid())

    # Test 90
    def test_otp_is_invalid_when_used(self):
        otp = self._make_otp(used=True)
        self.assertFalse(otp.is_valid())

    # Test 91
    def test_otp_is_invalid_when_too_many_attempts(self):
        otp = self._make_otp(attempts=5)
        self.assertFalse(otp.is_valid())

    # Test 92
    def test_otp_is_invalid_when_expired(self):
        from vaxsafe.models import OTPVerification
        otp = OTPVerification.objects.create(
            email="old@example.com",
            otp="999999",
            full_name="Old User",
            hashed_password="hash",
        )
        # Manually set created_at to 11 minutes ago
        OTPVerification.objects.filter(pk=otp.pk).update(
            created_at=timezone.now() - timedelta(minutes=11)
        )
        otp.refresh_from_db()
        self.assertFalse(otp.is_valid())

    # Test 93
    def test_otp_attempts_default_zero(self):
        otp = self._make_otp()
        self.assertEqual(otp.attempts, 0)

    # Test 94
    def test_otp_is_used_default_false(self):
        otp = self._make_otp()
        self.assertFalse(otp.is_used)


# ═══════════════════════════════════════════════
# 12. VACCINE SCHEDULE MODEL TESTS
# ═══════════════════════════════════════════════

class VaccineScheduleModelTest(TestCase):

    def setUp(self):
        self.user = make_admin()

    def _make_schedule(self, vaccine="COVID-19", dose="1st", days=21):
        from vaxsafe.models import VaccineSchedule
        return VaccineSchedule.objects.create(
            vaccine_name=vaccine,
            dose_number=dose,
            interval_days=days,
            created_by=self.user,
        )

    # Test 95
    def test_create_vaccine_schedule(self):
        s = self._make_schedule()
        self.assertEqual(s.vaccine_name, "COVID-19")

    # Test 96
    def test_vaccine_schedule_str(self):
        s = self._make_schedule()
        result = str(s)
        self.assertIn("COVID-19", result)

    # Test 97
    def test_vaccine_schedule_str_last_dose(self):
        from vaxsafe.models import VaccineSchedule
        s = VaccineSchedule.objects.create(
            vaccine_name="BCG", dose_number="Single", interval_days=0
        )
        self.assertIn("শেষ ডোজ", str(s))

    # Test 98
    def test_vaccine_schedule_is_active_default(self):
        s = self._make_schedule()
        self.assertTrue(s.is_active)

    # Test 99
    def test_vaccine_schedule_unique_together(self):
        from django.db import IntegrityError
        self._make_schedule(vaccine="MMR", dose="1st")
        with self.assertRaises(IntegrityError):
            self._make_schedule(vaccine="MMR", dose="1st")


# ═══════════════════════════════════════════════
# 13. FAMILY GROUP MODEL TESTS
# ═══════════════════════════════════════════════

class FamilyGroupModelTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def _make_group(self, name="Rahman Family"):
        from vaxsafe.models import FamilyGroup
        return FamilyGroup.objects.create(family_name=name, created_by=self.user)

    # Test 100
    def test_create_family_group(self):
        g = self._make_group()
        self.assertEqual(g.family_name, "Rahman Family")

    # Test 101
    def test_family_group_str(self):
        g = self._make_group()
        self.assertEqual(str(g), "Rahman Family")

    # Test 102
    def test_get_primary_admin_none_when_no_members(self):
        g = self._make_group()
        self.assertIsNone(g.get_primary_admin())

    # Test 103
    def test_get_primary_admin_returns_admin_member(self):
        from vaxsafe.models import FamilyGroup, FamilyGroupMember
        g = self._make_group()
        FamilyGroupMember.objects.create(
            family=g, user=self.user, role="Admin", is_active=True
        )
        admin = g.get_primary_admin()
        self.assertIsNotNone(admin)
        self.assertEqual(admin.role, "Admin")


# ═══════════════════════════════════════════════
# 14. FAMILY GROUP MEMBER MODEL TESTS
# ═══════════════════════════════════════════════

class FamilyGroupMemberModelTest(TestCase):

    def setUp(self):
        self.user = make_user()
        from vaxsafe.models import FamilyGroup
        self.group = FamilyGroup.objects.create(family_name="Test Family", created_by=self.user)

    def _make_member(self, role="Member"):
        from vaxsafe.models import FamilyGroupMember
        return FamilyGroupMember.objects.create(
            family=self.group,
            user=self.user,
            role=role,
            is_active=True,
        )

    # Test 104
    def test_create_group_member(self):
        m = self._make_member()
        self.assertEqual(m.role, "Member")

    # Test 105
    def test_group_member_str_with_user(self):
        m = self._make_member(role="Admin")
        result = str(m)
        self.assertIn("Admin", result)

    # Test 106
    def test_group_member_role_choices(self):
        from vaxsafe.models import FamilyGroupMember, FamilyGroup
        for role in ("Admin", "Guardian", "Member"):
            user = make_user(username=f"u_{role}")
            m = FamilyGroupMember.objects.create(
                family=self.group, user=user, role=role
            )
            self.assertEqual(m.role, role)

    # Test 107
    def test_group_member_can_view_default_false(self):
        m = self._make_member()
        self.assertFalse(m.can_view_others)

    # Test 108
    def test_group_member_can_edit_default_false(self):
        m = self._make_member()
        self.assertFalse(m.can_edit_others)


# ═══════════════════════════════════════════════
# 15. FAMILY INVITATION MODEL TESTS
# ═══════════════════════════════════════════════

class FamilyInvitationModelTest(TestCase):

    def setUp(self):
        self.user = make_user()
        from vaxsafe.models import FamilyGroup
        self.group = FamilyGroup.objects.create(family_name="Invite Family", created_by=self.user)

    def _make_invite(self, hours_ahead=24):
        from vaxsafe.models import FamilyInvitation
        return FamilyInvitation.objects.create(
            family=self.group,
            invited_by=self.user,
            email="guest@example.com",
            expires_at=timezone.now() + timedelta(hours=hours_ahead),
        )

    # Test 109
    def test_create_invitation(self):
        inv = self._make_invite()
        self.assertEqual(inv.email, "guest@example.com")

    # Test 110
    def test_invitation_str(self):
        inv = self._make_invite()
        result = str(inv)
        self.assertIn("guest@example.com", result)

    # Test 111
    def test_is_valid_fresh_invite(self):
        inv = self._make_invite()
        self.assertTrue(inv.is_valid())

    # Test 112
    def test_is_invalid_when_accepted(self):
        inv = self._make_invite()
        inv.is_accepted = True
        inv.save()
        self.assertFalse(inv.is_valid())

    # Test 113
    def test_is_invalid_when_expired(self):
        from vaxsafe.models import FamilyInvitation
        inv = FamilyInvitation.objects.create(
            family=self.group,
            invited_by=self.user,
            email="expired@example.com",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertFalse(inv.is_valid())

    # Test 114
    def test_invitation_token_unique(self):
        inv1 = self._make_invite()
        inv2 = self._make_invite()
        self.assertNotEqual(inv1.token, inv2.token)


# ═══════════════════════════════════════════════
# 16. CUSTOM VACCINE TYPE MODEL TESTS
# ═══════════════════════════════════════════════

class CustomVaccineTypeModelTest(TestCase):

    def setUp(self):
        self.user = make_admin()

    # Test 115
    def test_create_custom_vaccine_type(self):
        from vaxsafe.models import CustomVaccineType
        cvt = CustomVaccineType.objects.create(
            name="DengueVax", created_by=self.user
        )
        self.assertEqual(cvt.name, "DengueVax")

    # Test 116
    def test_custom_vaccine_type_str(self):
        from vaxsafe.models import CustomVaccineType
        cvt = CustomVaccineType.objects.create(name="MalariaVax")
        self.assertEqual(str(cvt), "MalariaVax")

    # Test 117
    def test_is_active_default_true(self):
        from vaxsafe.models import CustomVaccineType
        cvt = CustomVaccineType.objects.create(name="ZikaVax")
        self.assertTrue(cvt.is_active)

    # Test 118
    def test_notify_all_users_default_true(self):
        from vaxsafe.models import CustomVaccineType
        cvt = CustomVaccineType.objects.create(name="CholeraVax")
        self.assertTrue(cvt.notify_all_users)

    # Test 119
    def test_custom_vaccine_name_unique(self):
        from django.db import IntegrityError
        from vaxsafe.models import CustomVaccineType
        CustomVaccineType.objects.create(name="UniqueVax")
        with self.assertRaises(IntegrityError):
            CustomVaccineType.objects.create(name="UniqueVax")


# ═══════════════════════════════════════════════
# 17. EDGE CASE & INTEGRATION TESTS
# ═══════════════════════════════════════════════

class EdgeCaseTests(TestCase):

    def setUp(self):
        self.user = make_user()

    # Test 120
    def test_vaccine_without_family_member(self):
        from vaxsafe.models import Vaccine
        v = Vaccine.objects.create(
            user=self.user, name="BCG", dose_number="Single",
            date_administered=date.today(), status="Completed"
        )
        self.assertIsNone(v.family_member)

    # Test 121
    def test_multiple_vaccines_same_user(self):
        from vaxsafe.models import Vaccine
        for name in ("COVID-19", "BCG", "MMR"):
            Vaccine.objects.create(
                user=self.user, name=name, dose_number="1st",
                date_administered=date.today(), status="Completed"
            )
        self.assertEqual(Vaccine.objects.filter(user=self.user).count(), 3)

    # Test 122
    def test_reminder_for_family_member(self):
        from vaxsafe.models import FamilyMember, VaccineReminder
        member = FamilyMember.objects.create(user=self.user, name="Kid", relation="Child")
        reminder = VaccineReminder.objects.create(
            user=self.user,
            vaccine_name="Polio",
            reminder_date=date.today() + timedelta(days=7),
            reminder_time=time(10, 0),
            family_member=member,
        )
        self.assertEqual(reminder.family_member.name, "Kid")

    # Test 123
    def test_otp_after_4_attempts_still_valid(self):
        from vaxsafe.models import OTPVerification
        otp = OTPVerification.objects.create(
            email="a@b.com", otp="111111",
            full_name="Test", hashed_password="hash",
            attempts=4,
        )
        self.assertTrue(otp.is_valid())

    # Test 124
    def test_news_long_content_reading_time(self):
        from vaxsafe.models import News
        long_content = " ".join(["word"] * 400)  # ~2 min read
        n = News.objects.create(
            title="Long Article", summary="S", content=long_content
        )
        result = n.get_reading_time()
        self.assertIn("2", result)

    # Test 125
    def test_vaccination_center_distance_same_point(self):
        from vaxsafe.models import VaccinationCenter
        c = VaccinationCenter.objects.create(
            name="Same Point", address="X", city="Dhaka",
            latitude=23.81, longitude=90.41
        )
        dist = c.get_distance_from(23.81, 90.41)
        self.assertEqual(dist, 0.0)
