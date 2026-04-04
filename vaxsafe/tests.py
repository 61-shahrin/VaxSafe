"""
VaxSafe2 - Essential Unit Tests (15)
=====================================
Run command:
    python manage.py test vaxsafe
"""

import time
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from vaxsafe.models import Profile, FamilyMember, Vaccine, Reminder
from vaxsafe.forms import ProfileForm, VaccineForm


# Helper: create user quickly
def make_user(username='test@test.com', password='pass1234'):
    user = User.objects.create_user(
        username=username, email=username, password=password, first_name='Test'
    )
    Profile.objects.create(user=user)
    return user


# TEST 1 - Login: correct credentials redirect to dashboard
class Test01_LoginSuccess(TestCase):
    def setUp(self):
        self.client = Client()
        make_user('login@test.com', 'mypass123')

    def test_correct_credentials_redirect_to_dashboard(self):
        response = self.client.post(reverse('login'), {
            'username': 'login@test.com',
            'password': 'mypass123'
        })
        self.assertRedirects(response, reverse('dashboard'))


# TEST 2 - Login: wrong password is blocked
class Test02_LoginFailure(TestCase):
    def setUp(self):
        self.client = Client()
        make_user('wrongpass@test.com', 'correct123')

    def test_wrong_password_stays_on_login(self):
        response = self.client.post(reverse('login'), {
            'username': 'wrongpass@test.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        msgs = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('Invalid' in m or 'invalid' in m for m in msgs))


# TEST 3 - Registration: duplicate email is blocked
class Test03_RegisterDuplicateEmail(TestCase):
    def setUp(self):
        self.client = Client()
        make_user('existing@test.com', 'pass1234')

    def test_duplicate_email_shows_error(self):
        response = self.client.post(reverse('register'), {
            'full_name': 'New User',
            'email': 'existing@test.com',
            'password': 'newpass123',
            'reset_password': 'newpass123'
        })
        self.assertEqual(response.status_code, 200)
        msgs = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('registered' in m.lower() or 'use' in m.lower() for m in msgs))


# TEST 4 - Registration: password mismatch is blocked
class Test04_RegisterPasswordMismatch(TestCase):
    def setUp(self):
        self.client = Client()

    def test_mismatched_passwords_show_error(self):
        response = self.client.post(reverse('register'), {
            'full_name': 'Someone',
            'email': 'mismatch@test.com',
            'password': 'pass1111',
            'reset_password': 'pass2222'
        })
        self.assertEqual(response.status_code, 200)
        msgs = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('match' in m.lower() for m in msgs))


# TEST 5 - Dashboard: not accessible without login
class Test05_DashboardRequiresLogin(TestCase):
    def test_unauthenticated_user_redirected(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


# TEST 6 - OTP: correct OTP creates account
class Test06_OTPVerificationSuccess(TestCase):
    def setUp(self):
        self.client = Client()

    def test_correct_otp_creates_user_and_redirects(self):
        session = self.client.session
        session['otp'] = '654321'
        session['otp_time'] = time.time()
        session['temp_user'] = {
            'full_name': 'New Person',
            'email': 'otpuser@test.com',
            'password': 'mypass123'
        }
        session.save()

        response = self.client.post(reverse('verify'), {
            'otp': '654321',
            'action': 'submit'
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(User.objects.filter(username='otpuser@test.com').exists())


# TEST 7 - OTP: expired OTP is rejected
class Test07_OTPExpired(TestCase):
    def setUp(self):
        self.client = Client()

    def test_expired_otp_shows_error(self):
        session = self.client.session
        session['otp'] = '111111'
        session['otp_time'] = time.time() - 400  # 400 seconds ago = expired
        session['temp_user'] = {
            'full_name': 'Expired User',
            'email': 'expired@test.com',
            'password': 'mypass123'
        }
        session.save()

        response = self.client.post(reverse('verify'), {
            'otp': '111111',
            'action': 'submit'
        })
        self.assertEqual(response.status_code, 200)
        msgs = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('expired' in m.lower() for m in msgs))


# TEST 8 - Vaccine: adding a vaccine saves to database
class Test08_AddVaccineSuccess(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user('vaccineadd@test.com')
        self.client.login(username='vaccineadd@test.com', password='pass1234')

    def test_valid_vaccine_saved_to_database(self):
        future_date = (date.today() + timedelta(days=10)).isoformat()
        self.client.post(reverse('add_vaccine'), {
            'name': 'COVID-19',
            'dose_number': '1st',
            'date_administered': future_date,
            'status': 'Scheduled',
        })
        self.assertTrue(
            Vaccine.objects.filter(name='COVID-19', user=self.user).exists()
        )


# TEST 9 - Vaccine: cannot view or delete another user's vaccine (Security)
class Test09_VaccineDataIsolation(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = make_user('user1@test.com')
        self.user2 = make_user('user2@test.com')
        self.user2_vaccine = Vaccine.objects.create(
            user=self.user2,
            name='MMR',
            dose_number='1st',
            date_administered=date.today(),
            status='Completed'
        )
        self.client.login(username='user1@test.com', password='pass1234')

    def test_cannot_view_other_users_vaccine(self):
        response = self.client.get(
            reverse('vaccine_detail', args=[self.user2_vaccine.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_delete_other_users_vaccine(self):
        self.client.post(reverse('delete_vaccine', args=[self.user2_vaccine.id]))
        self.assertTrue(Vaccine.objects.filter(id=self.user2_vaccine.id).exists())


# TEST 10 - Vaccine Model: overdue and upcoming detection works correctly
class Test10_VaccineOverdueLogic(TestCase):
    def setUp(self):
        self.user = make_user('overdue@test.com')
        self.past_vaccine = Vaccine.objects.create(
            user=self.user,
            name='Influenza',
            dose_number='Single',
            date_administered=date.today() - timedelta(days=5),
            status='Scheduled'
        )
        self.future_vaccine = Vaccine.objects.create(
            user=self.user,
            name='COVID-19',
            dose_number='2nd',
            date_administered=date.today() + timedelta(days=5),
            status='Scheduled'
        )

    def test_past_scheduled_vaccine_is_overdue(self):
        self.assertTrue(self.past_vaccine.is_overdue())

    def test_future_vaccine_is_not_overdue(self):
        self.assertFalse(self.future_vaccine.is_overdue())

    def test_future_vaccine_is_upcoming(self):
        self.assertTrue(self.future_vaccine.is_upcoming())


# TEST 11 - Family Member: add and delete work correctly
class Test11_FamilyMemberCRUD(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user('family@test.com')
        self.client.login(username='family@test.com', password='pass1234')

    def test_add_family_member(self):
        self.client.post(reverse('addfamilymember'), {
            'name': 'Younger Brother',
            'relation': 'Sibling',
            'gender': 'Male',
            'age': 15,
        })
        self.assertTrue(
            FamilyMember.objects.filter(name='Younger Brother', user=self.user).exists()
        )

    def test_delete_family_member(self):
        member = FamilyMember.objects.create(
            user=self.user, name='To Delete', relation='Child', age=5
        )
        self.client.post(reverse('delete_family_member', args=[member.id]))
        self.assertFalse(FamilyMember.objects.filter(id=member.id).exists())


# TEST 12 - Reminder Model: Active/Missed/Completed status is correct
class Test12_ReminderStatus(TestCase):
    def setUp(self):
        self.user = make_user('reminder@test.com')

    def test_future_reminder_is_active(self):
        r = Reminder.objects.create(
            user=self.user, vaccine_name='BCG',
            scheduled_datetime=timezone.now() + timedelta(days=2),
            family_member='Mom'
        )
        self.assertEqual(r.status, 'Active')

    def test_past_reminder_is_missed(self):
        r = Reminder.objects.create(
            user=self.user, vaccine_name='Polio',
            scheduled_datetime=timezone.now() - timedelta(days=1),
            family_member='Dad'
        )
        self.assertEqual(r.status, 'Missed')

    def test_completed_reminder_status(self):
        r = Reminder.objects.create(
            user=self.user, vaccine_name='MMR',
            scheduled_datetime=timezone.now() - timedelta(hours=1),
            family_member='Me', completed=True
        )
        self.assertEqual(r.status, 'Completed')


# TEST 13 - ProfileForm: invalid blood group is rejected
class Test13_ProfileFormValidation(TestCase):
    def test_invalid_blood_group_rejected(self):
        form = ProfileForm(data={'blood_group': 'XYZ'})
        form.is_valid()
        self.assertIn('blood_group', form.errors)

    def test_valid_blood_group_accepted(self):
        form = ProfileForm(data={'blood_group': 'O+'})
        form.is_valid()
        self.assertNotIn('blood_group', form.errors)

    def test_blood_group_saved_uppercase(self):
        form = ProfileForm(data={'blood_group': 'a+'})
        form.is_valid()
        if 'blood_group' not in form.errors:
            self.assertEqual(form.cleaned_data['blood_group'], 'A+')


# TEST 14 - VaccineForm: future date valid, very old date rejected
class Test14_VaccineFormDateValidation(TestCase):
    def setUp(self):
        self.user = make_user('formdate@test.com')

    def test_normal_future_date_is_valid(self):
        future = (date.today() + timedelta(days=30)).isoformat()
        form = VaccineForm(
            data={
                'name': 'COVID-19',
                'dose_number': '1st',
                'date_administered': future,
                'status': 'Scheduled',
            },
            user=self.user
        )
        form.is_valid()
        self.assertNotIn('date_administered', form.errors)

    def test_too_old_date_is_invalid(self):
        very_old = (date.today() - timedelta(days=40000)).isoformat()
        form = VaccineForm(
            data={
                'name': 'Influenza',
                'dose_number': 'Single',
                'date_administered': very_old,
                'status': 'Completed',
            },
            user=self.user
        )
        form.is_valid()
        self.assertIn('date_administered', form.errors)


# TEST 15 - Dashboard: shows only the logged-in user's vaccine counts
class Test15_DashboardCountsCorrect(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user('dash@test.com')
        self.other = make_user('other@test.com')

        Vaccine.objects.create(
            user=self.user, name='COVID-19', dose_number='1st',
            date_administered=date.today() + timedelta(days=5),
            status='Scheduled'
        )
        Vaccine.objects.create(
            user=self.user, name='MMR', dose_number='1st',
            date_administered=date.today() + timedelta(days=10),
            status='Scheduled'
        )
        # Other user's vaccine - should not appear in count
        Vaccine.objects.create(
            user=self.other, name='Polio', dose_number='Single',
            date_administered=date.today() + timedelta(days=3),
            status='Scheduled'
        )

        self.client.login(username='dash@test.com', password='pass1234')

    def test_dashboard_shows_only_own_vaccine_count(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_vaccines'], 2)
        self.assertEqual(response.context['upcoming_count'], 2)
