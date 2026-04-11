# tests.py - Top 50 Unit Tests for VaxSafe
# Run with: python manage.py test vaxsafe

from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from vaxsafe.models import (
    Profile, FamilyMember, Vaccine, Notification,
    VaccineReminder, FamilyGroup, FamilyGroupMember,
    FamilyInvitation, News,
)
from vaxsafe.forms import (
    ProfileForm, FamilyMemberForm, VaccineForm, VaccineReminderForm,
)


# ── Helpers ──────────────────────────────────────────────────

def make_user(username='testuser', password='Test@1234', email=None):
    email = email or f'{username}@example.com'
    # first_name ইচ্ছাকৃতভাবে blank রাখা হয়েছে
    # যাতে get_full_name() username-এ fallback করে
    user = User.objects.create_user(
        username=username, email=email, password=password
    )
    Profile.objects.get_or_create(user=user)
    return user


def make_member(user, name='Alice', relation='Child'):
    return FamilyMember.objects.create(
        user=user, name=name, relation=relation, age=10
    )


def make_vaccine(user, member=None):
    return Vaccine.objects.create(
        user=user, family_member=member,
        name='COVID-19', dose_number='1st',
        date_administered=date.today(), status='Completed'
    )


# ── 1. MODEL TESTS (1–19) ────────────────────────────────────

class ModelTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.profile = Profile.objects.get(user=self.user)

    # 1. Profile __str__ contains username
    def test_profile_str(self):
        self.assertIn(self.user.username, str(self.profile))

    # 2. Profile get_full_name fallback to username when no name
    def test_profile_get_full_name_fallback(self):
        self.assertEqual(self.profile.get_full_name(), self.user.username)

    # 3. Profile get_full_name returns full name when set
    def test_profile_get_full_name(self):
        self.user.first_name = 'Rahim'
        self.user.last_name = 'Uddin'
        self.user.save()
        self.assertEqual(self.profile.get_full_name(), 'Rahim Uddin')

    # 4. FamilyMember __str__ contains name and relation
    def test_family_member_str(self):
        m = make_member(self.user)
        self.assertIn('Alice', str(m))
        self.assertIn('Child', str(m))

    # 5. FamilyMember calculate_age from date_of_birth
    def test_family_member_age_from_dob(self):
        m = make_member(self.user)
        m.date_of_birth = date.today() - timedelta(days=365 * 8)
        m.age = None
        m.save()
        self.assertIn(m.calculate_age(), [7, 8])

    # 6. FamilyMember calculate_age fallback to age field
    def test_family_member_age_fallback(self):
        m = make_member(self.user)
        m.date_of_birth = None
        m.age = 15
        m.save()
        self.assertEqual(m.calculate_age(), 15)

    # 7. FamilyMember ordering is alphabetical by name
    def test_family_member_ordering(self):
        make_member(self.user, 'Zara')
        make_member(self.user, 'Abir')
        names = list(
            FamilyMember.objects.filter(user=self.user).values_list('name', flat=True)
        )
        self.assertEqual(names, sorted(names))

    # 8. Vaccine __str__ includes member name when member set
    def test_vaccine_str_with_member(self):
        m = make_member(self.user)
        v = make_vaccine(self.user, m)
        self.assertIn('Alice', str(v))

    # 9. Vaccine default status is Scheduled
    def test_vaccine_default_status(self):
        v = Vaccine.objects.create(
            user=self.user, name='Influenza',
            dose_number='Single', date_administered=date.today()
        )
        self.assertEqual(v.status, 'Scheduled')

    # 10. Vaccine get_recipient_name without member matches user's display name
    def test_vaccine_recipient_no_member(self):
        v = make_vaccine(self.user)
        expected = self.user.get_full_name() or self.user.username
        self.assertEqual(v.get_recipient_name(), expected)

    # 11. Notification default is_read is False
    def test_notification_default_unread(self):
        n = Notification.objects.create(
            user=self.user, title='T', message='M'
        )
        self.assertFalse(n.is_read)

    # 12. Notification ordering is newest first
    def test_notification_ordering(self):
        Notification.objects.create(user=self.user, title='First', message='A')
        Notification.objects.create(user=self.user, title='Second', message='B')
        first = Notification.objects.filter(user=self.user).first()
        self.assertEqual(first.title, 'Second')

    # 13. VaccineReminder default is_sent is False
    def test_reminder_default_not_sent(self):
        vr = VaccineReminder.objects.create(
            user=self.user, vaccine_name='BCG',
            reminder_date=date.today() + timedelta(days=7)
        )
        self.assertFalse(vr.is_sent)

    # 14. VaccineReminder ordering is soonest first
    def test_reminder_ordering(self):
        VaccineReminder.objects.create(
            user=self.user, vaccine_name='A',
            reminder_date=date.today() + timedelta(days=10)
        )
        VaccineReminder.objects.create(
            user=self.user, vaccine_name='B',
            reminder_date=date.today() + timedelta(days=2)
        )
        first = VaccineReminder.objects.filter(user=self.user).first()
        self.assertEqual(first.vaccine_name, 'B')

    # 15. FamilyInvitation is_valid returns True for fresh invite
    def test_invitation_is_valid(self):
        fg = FamilyGroup.objects.create(family_name='Fam', created_by=self.user)
        inv = FamilyInvitation.objects.create(
            family=fg, invited_by=self.user, email='g@test.com',
            role='Member', expires_at=timezone.now() + timedelta(days=7)
        )
        self.assertTrue(inv.is_valid())

    # 16. FamilyInvitation is_valid returns False when expired
    def test_invitation_expired(self):
        fg = FamilyGroup.objects.create(family_name='Fam', created_by=self.user)
        inv = FamilyInvitation.objects.create(
            family=fg, invited_by=self.user, email='g@test.com',
            role='Member', expires_at=timezone.now() - timedelta(days=1)
        )
        self.assertFalse(inv.is_valid())

    # 17. News slug is auto-generated from title
    def test_news_slug_auto(self):
        news = News.objects.create(
            title='VaxSafe News', summary='s', content='c', author=self.user
        )
        self.assertIn('vaxsafe', news.slug)

    # 18. Duplicate News titles get unique slugs
    def test_news_unique_slug(self):
        News.objects.create(title='Same Title', summary='s', content='c', author=self.user)
        n2 = News.objects.create(title='Same Title', summary='s', content='c', author=self.user)
        self.assertNotEqual(n2.slug, 'same-title')

    # 19. News increment_views increases count by 1
    def test_news_increment_views(self):
        news = News.objects.create(
            title='Views Test', summary='s', content='c', author=self.user
        )
        news.increment_views()
        news.refresh_from_db()
        self.assertEqual(news.views, 1)


# ── 2. FORM TESTS (20–32) ────────────────────────────────────

class FormTests(TestCase):

    def setUp(self):
        self.user = make_user()

    # 20. ProfileForm valid data passes
    def test_profile_form_valid(self):
        form = ProfileForm(data={
            'mobile': '01712345678', 'gender': 'Male',
            'blood_group': 'O+', 'profession': 'Doctor',
            'address': 'Dhaka', 'date_of_birth': '1990-01-01',
        })
        self.assertTrue(form.is_valid())

    # 21. ProfileForm rejects invalid blood group
    def test_profile_form_invalid_blood_group(self):
        form = ProfileForm(data={'blood_group': 'Z+'})
        self.assertFalse(form.is_valid())
        self.assertIn('blood_group', form.errors)

    # 22. ProfileForm blood group is uppercased on clean
    def test_profile_form_blood_group_uppercase(self):
        form = ProfileForm(data={
            'mobile': '01712345678', 'blood_group': 'o+'
        })
        form.is_valid()
        if 'blood_group' not in form.errors:
            self.assertEqual(form.cleaned_data['blood_group'], 'O+')

    # 23. ProfileForm rejects mobile shorter than 10 digits
    def test_profile_form_short_mobile(self):
        form = ProfileForm(data={'mobile': '123'})
        self.assertFalse(form.is_valid())
        self.assertIn('mobile', form.errors)

    # 24. FamilyMemberForm valid with age provided
    def test_family_member_form_valid(self):
        form = FamilyMemberForm(data={'name': 'Bob', 'relation': 'Child', 'age': 5})
        self.assertTrue(form.is_valid())

    # 25. FamilyMemberForm invalid when neither age nor dob given
    def test_family_member_form_no_age_or_dob(self):
        form = FamilyMemberForm(data={'name': 'X', 'relation': 'Sibling'})
        self.assertFalse(form.is_valid())

    # 26. FamilyMemberForm requires name field
    def test_family_member_form_name_required(self):
        form = FamilyMemberForm(data={'relation': 'Spouse', 'age': 30})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    # 27. VaccineForm valid data passes
    def test_vaccine_form_valid(self):
        form = VaccineForm(user=self.user, data={
            'name': 'COVID-19', 'dose_number': '1st',
            'date_administered': date.today().isoformat(),
            'status': 'Completed',
        })
        self.assertTrue(form.is_valid(), form.errors)

    # 28. VaccineForm rejects next_dose_date before date_administered
    def test_vaccine_form_next_dose_invalid(self):
        form = VaccineForm(user=self.user, data={
            'name': 'COVID-19', 'dose_number': '1st',
            'date_administered': date.today().isoformat(),
            'next_dose_date': (date.today() - timedelta(days=1)).isoformat(),
            'status': 'Scheduled',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('next_dose_date', form.errors)

    # 29. VaccineForm auto-changes past Scheduled to Overdue
    def test_vaccine_form_auto_overdue(self):
        form = VaccineForm(user=self.user, data={
            'name': 'Influenza', 'dose_number': 'Single',
            'date_administered': (date.today() - timedelta(days=10)).isoformat(),
            'status': 'Scheduled',
        })
        form.is_valid()
        self.assertEqual(form.cleaned_data.get('status'), 'Overdue')

    # 30. VaccineForm family_member queryset only shows user's members
    def test_vaccine_form_member_queryset_scoped(self):
        other = make_user('other2', email='other2@test.com')
        make_member(other, name='StrangerChild')
        form = VaccineForm(user=self.user)
        qs = form.fields['family_member'].queryset
        self.assertFalse(qs.filter(name='StrangerChild').exists())

    # 31. VaccineReminderForm valid with future date
    def test_reminder_form_valid(self):
        form = VaccineReminderForm(data={
            'vaccine_name': 'BCG',
            'reminder_date': (date.today() + timedelta(days=3)).isoformat(),
            'reminder_time': '09:00',
        })
        self.assertTrue(form.is_valid(), form.errors)

    # 32. VaccineReminderForm rejects past date
    def test_reminder_form_past_date(self):
        form = VaccineReminderForm(data={
            'vaccine_name': 'BCG',
            'reminder_date': (date.today() - timedelta(days=1)).isoformat(),
            'reminder_time': '09:00',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('reminder_date', form.errors)


# ── 3. VIEW TESTS (33–50) ────────────────────────────────────

class ViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def login(self):
        self.client.login(username='testuser', password='Test@1234')

    # 33. Home page returns HTTP 200
    def test_home_200(self):
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)

    # 34. Dashboard redirects unauthenticated user to login
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, '/login/?next=/dashboard/')

    # 35. Dashboard accessible after login
    def test_dashboard_logged_in(self):
        self.login()
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)

    # 36. Correct login redirects to dashboard
    def test_login_success(self):
        response = self.client.post(
            reverse('login'), {'username': 'testuser', 'password': 'Test@1234'}
        )
        self.assertRedirects(response, reverse('dashboard'))

    # 37. Wrong password stays on login page
    def test_login_wrong_password(self):
        response = self.client.post(
            reverse('login'), {'username': 'testuser', 'password': 'wrong'}
        )
        self.assertEqual(response.status_code, 200)

    # 38. Logout redirects to home page
    def test_logout(self):
        self.login()
        self.assertRedirects(self.client.get(reverse('logout')), reverse('home'))

    # 39. Register with existing email shows error
    def test_register_duplicate_email(self):
        response = self.client.post(reverse('register'), {
            'full_name': 'Dup', 'email': 'testuser@example.com',
            'password': 'Pass1234', 'reset_password': 'Pass1234',
        })
        msgs = [str(m) for m in response.context['messages']]
        self.assertTrue(any('already' in m.lower() for m in msgs))

    # 40. Register with mismatched passwords shows error
    def test_register_password_mismatch(self):
        response = self.client.post(reverse('register'), {
            'full_name': 'New', 'email': 'new@test.com',
            'password': 'Pass1234', 'reset_password': 'Different',
        })
        msgs = [str(m) for m in response.context['messages']]
        self.assertTrue(any('match' in m.lower() for m in msgs))

    # 41. Add family member creates DB record
    def test_add_family_member(self):
        self.login()
        self.client.post(reverse('addfamilymember'), {
            'name': 'Rafi', 'relation': 'Child', 'age': 6
        })
        self.assertTrue(
            FamilyMember.objects.filter(name='Rafi', user=self.user).exists()
        )

    # 42. Editing another user's family member returns 404
    def test_cannot_edit_other_member(self):
        self.login()
        other = make_user('other3', email='other3@test.com')
        m = make_member(other, 'Private')
        response = self.client.get(reverse('edit_family_member', args=[m.id]))
        self.assertEqual(response.status_code, 404)

    # 43. Deleting own family member removes it from DB
    def test_delete_family_member(self):
        self.login()
        m = make_member(self.user)
        self.client.post(reverse('delete_family_member', args=[m.id]))
        self.assertFalse(FamilyMember.objects.filter(id=m.id).exists())

    # 44. Add vaccine creates DB record
    def test_add_vaccine(self):
        self.login()
        count = Vaccine.objects.filter(user=self.user).count()
        self.client.post(reverse('add_vaccine'), {
            'name': 'Influenza', 'dose_number': 'Single',
            'date_administered': date.today().isoformat(),
            'status': 'Completed',
        })
        self.assertEqual(Vaccine.objects.filter(user=self.user).count(), count + 1)

    # 45. Deleting another user's vaccine returns 404
    def test_cannot_delete_other_vaccine(self):
        self.login()
        other = make_user('vother', email='vother@test.com')
        v = make_vaccine(other)
        response = self.client.post(reverse('delete_vaccine', args=[v.id]))
        self.assertEqual(response.status_code, 404)

    # 46. Setting reminder creates VaccineReminder and Notification
    def test_set_reminder_creates_objects(self):
        self.login()
        future = (date.today() + timedelta(days=5)).isoformat()
        self.client.post(reverse('set_reminder'), {
            'vaccine_name': 'Typhoid',
            'reminder_date': future,
            'reminder_time': '08:00',
        })
        self.assertTrue(VaccineReminder.objects.filter(user=self.user).exists())
        self.assertTrue(
            Notification.objects.filter(user=self.user, notif_type='reminder').exists()
        )

    # 47. Deleting another user's reminder returns 404
    def test_cannot_delete_other_reminder(self):
        self.login()
        other = make_user('rother', email='rother@test.com')
        vr = VaccineReminder.objects.create(
            user=other, vaccine_name='BCG',
            reminder_date=date.today() + timedelta(days=5)
        )
        response = self.client.post(reverse('delete_reminder', args=[vr.id]))
        self.assertEqual(response.status_code, 404)

    # 48. Visiting notification list marks all unread as read
    def test_notification_list_marks_read(self):
        self.login()
        Notification.objects.create(
            user=self.user, title='N', message='m', is_read=False
        )
        self.client.get(reverse('notification_list'))
        self.assertFalse(
            Notification.objects.filter(user=self.user, is_read=False).exists()
        )

    # 49. Deleting another user's notification returns 404
    def test_cannot_delete_other_notification(self):
        self.login()
        other = make_user('nother', email='nother@test.com')
        n = Notification.objects.create(user=other, title='X', message='x')
        response = self.client.post(reverse('delete_notification', args=[n.id]))
        self.assertEqual(response.status_code, 404)

    # 50. unread_notif_count correctly injected into template context
    def test_unread_notif_count_in_context(self):
        self.login()
        Notification.objects.create(user=self.user, title='T1', message='m', is_read=False)
        Notification.objects.create(user=self.user, title='T2', message='m', is_read=False)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context.get('unread_notif_count'), 2)
