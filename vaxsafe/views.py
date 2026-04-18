import re
import json
import random
import time
from datetime import timedelta
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db.models import Count, Q

from .models import (
    Profile, FamilyMember, FamilyGroupMember, FamilyGroup,
    FamilyInvitation, Reminder, Update, Vaccine,
    VaccinationCenter, News, VaccineUpdate,
    Notification, VaccineReminder, VaccineSchedule,OTPVerification,
)
from .forms import (
    ProfileForm, FamilyMemberForm, VaccineForm,
    FamilyCreateForm, FamilyInviteForm, AdminTransferForm,
    VaccineReminderForm,
    VaccineApplicationForm,
)

# =====================================================
# 🔔 NOTIFICATION HELPER FUNCTIONS
# =====================================================

def _send_vaccine_scheduled_notification(vaccine, target_user):
    recipient_name = vaccine.get_recipient_name()
    title = f"💉 {vaccine.name} — {vaccine.dose_number} নির্ধারিত"
    msg_lines = [
        f"Admin আপনার / আপনার পরিবারের সদস্য ({recipient_name}) এর জন্য",
        f"{vaccine.name} ({vaccine.dose_number}) টিকা",
        f"📅 তারিখ: {vaccine.date_administered.strftime('%d %B %Y')}",
    ]
    if vaccine.next_dose_date:
        msg_lines.append(f"📌 পরবর্তী ডোজ: {vaccine.next_dose_date.strftime('%d %B %Y')}")
    if vaccine.location:
        msg_lines.append(f"📍 স্থান: {vaccine.location}")
    if vaccine.healthcare_provider:
        msg_lines.append(f"👨‍⚕️ স্বাস্থ্যকর্মী: {vaccine.healthcare_provider}")
    full_msg = "\n".join(msg_lines)
    Notification.objects.create(user=target_user, title=title, message=full_msg, notif_type='reminder')
    if target_user.email:
        try:
            send_mail(
                subject=f"VaxSafe — {vaccine.name} টিকা নির্ধারিত",
                message=f"{title}\n\n{full_msg}\n\n---\nVaxSafe Vaccination Management",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[target_user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"[VaxSafe] Email error (vaccine scheduled): {e}")


def _send_vaccine_completed_notification(vaccine):
    target_user    = vaccine.user
    recipient_name = vaccine.get_recipient_name()
    title = f"✅ {vaccine.name} — {vaccine.dose_number} সম্পন্ন!"
    msg_lines = [
        f"অভিনন্দন! {recipient_name} এর {vaccine.name} ({vaccine.dose_number})",
        "টিকা সফলভাবে সম্পন্ন হয়েছে।",
    ]
    if vaccine.next_dose_date:
        msg_lines += [
            "",
            f"📅 পরবর্তী ডোজের তারিখ: {vaccine.next_dose_date.strftime('%d %B %Y')}",
            "অনুগ্রহ করে এই তারিখে টিকা নিতে ভুলবেন না।",
        ]
    else:
        msg_lines.append("\n🎉 এটি এই টিকার সর্বশেষ ডোজ ছিল।")
    full_msg = "\n".join(msg_lines)
    Notification.objects.create(user=target_user, title=title, message=full_msg, notif_type='update')
    if target_user.email:
        try:
            send_mail(
                subject=f"VaxSafe — {vaccine.name} {vaccine.dose_number} সম্পন্ন",
                message=f"{title}\n\n{full_msg}\n\n---\nVaxSafe",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[target_user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"[VaxSafe] Email error (vaccine completed): {e}")


def _send_reminder_notification(vr, target_user):
    recipient = vr.get_recipient_name()
    title = f"⏰ রিমাইন্ডার: {vr.vaccine_name}"
    msg_lines = [
        f"Admin '{recipient}' এর জন্য '{vr.vaccine_name}' টিকার রিমাইন্ডার সেট করেছেন।",
        f"📅 তারিখ: {vr.reminder_date.strftime('%d %B %Y')}",
        f"⏰ সময়: {vr.reminder_time.strftime('%I:%M %p')}",
    ]
    if vr.note:
        msg_lines.append(f"📝 নোট: {vr.note}")
    full_msg = "\n".join(msg_lines)
    Notification.objects.create(user=target_user, title=title, message=full_msg, notif_type='reminder')
    if target_user.email:
        try:
            send_mail(
                subject=f"VaxSafe — রিমাইন্ডার: {vr.vaccine_name} ({recipient})",
                message=f"{title}\n\n{full_msg}\n\n---\nVaxSafe",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[target_user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"[VaxSafe] Email error (reminder): {e}")


# =====================================================
# HELPER: সব user এর family members → JSON
# =====================================================

def _build_user_family_json(all_users):
    """প্রতিটি user এর family members একটি JSON dict এ রাখো।"""
    data = {}
    for u in all_users:
        members = FamilyMember.objects.filter(user=u).order_by('name')
        data[str(u.id)] = [
            {'id': m.id, 'name': f"{m.name} ({m.relation})"}
            for m in members
        ]
    return json.dumps(data)


# =====================================================
# AUTHENTICATION
# =====================================================

def validate_password(password):
    errors = []
    if len(password) < 8:
        errors.append("Password কমপক্ষে ৮ character হতে হবে।")
    if not re.search(r'[A-Z]', password):
        errors.append("কমপক্ষে একটি বড় হাতের অক্ষর (A-Z) দিতে হবে।")
    if not re.search(r'[a-z]', password):
        errors.append("কমপক্ষে একটি ছোট হাতের অক্ষর (a-z) দিতে হবে।")
    if not re.search(r'[0-9]', password):
        errors.append("কমপক্ষে একটি সংখ্যা (0-9) দিতে হবে।")
    if not re.search(r'[!@#$%^&*(),.?\":{}|<>@]', password):
        errors.append("কমপক্ষে একটি special character (!@#$% ইত্যাদি) দিতে হবে।")
    return errors


def _generate_otp():
    """৬ digit random OTP।"""
    return str(random.randint(100000, 999999))


def _send_otp_email(email, otp, full_name):
    """Registration OTP email পাঠাও।"""
    subject = "VaxSafe — আপনার OTP কোড"
    body = f"""
HELLO {full_name},

আপনার VaxSafe Registration OTP কোড:

    ━━━━━━━━━━━━━━
         {otp}
    ━━━━━━━━━━━━━━

এই কোডটি ১০ মিনিটের মধ্যে ব্যবহার করুন।
কেউ যদি এই কোড চায় তাকে দেবেন না।

— VaxSafe Team
    """
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"[VaxSafe] OTP email error: {e}")
        return False


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == "POST":
        full_name        = request.POST.get("full_name", "").strip()
        email            = request.POST.get("email", "").strip().lower()
        password         = request.POST.get("password", "")
        confirm_password = request.POST.get("reset_password", "")

        # ── Validation ──────────────────────────────────────────
        if not all([full_name, email, password, confirm_password]):
            messages.error(request, "সব তথ্য পূরণ করতে হবে।")
            return render(request, "htmlpages/register.html")

        if password != confirm_password:
            messages.error(request, "দুটো Password মিলছে না।")
            return render(request, "htmlpages/register.html")

        pw_errors = validate_password(password)
        if pw_errors:
            for err in pw_errors:
                messages.error(request, err)
            return render(request, "htmlpages/register.html")

        if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
            messages.error(request, "এই Email দিয়ে আগেই account তৈরি আছে।")
            return render(request, "htmlpages/register.html")

        # ── OTP তৈরি ও DB তে save ────────────────────────────────
        # পুরনো pending OTP মুছে দাও (একই email এর জন্য)
        OTPVerification.objects.filter(email=email, is_used=False).delete()

        otp = _generate_otp()

        # Password hash করে save করো (plain text save করা unsafe)
        from django.contrib.auth.hashers import make_password
        otpobj = OTPVerification.objects.create(
            email           = email,
            otp             = otp,
            full_name       = full_name,
            hashed_password = make_password(password),
        )

        # ── Email পাঠাও ──────────────────────────────────────────
        sent = _send_otp_email(email, otp, full_name)
        if not sent:
            messages.error(request, "❌ Email পাঠাতে সমস্যা হয়েছে। আবার চেষ্টা করুন।")
            otpobj.delete()
            return render(request, "htmlpages/register.html")

        # ── Session এ email রাখো (verify page এ দরকার হবে) ──────
        request.session['pending_otp_email'] = email

        messages.success(request, f"✅ {email} এ একটি OTP পাঠানো হয়েছে। ১০ মিনিটের মধ্যে verify করুন।")
        return redirect('verify_otp')

    return render(request, "htmlpages/register.html")


def verify_otp(request):
    """OTP verify করে account তৈরি করো।"""
    email = request.session.get('pending_otp_email')
    if not email:
        messages.error(request, "Session expired। আবার register করুন।")
        return redirect('register')

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()

        try:
            otpobj = OTPVerification.objects.filter(
                email=email, is_used=False
            ).latest('created_at')
        except OTPVerification.DoesNotExist:
            messages.error(request, "❌ OTP পাওয়া যায়নি। আবার register করুন।")
            return redirect('register')

        if not otpobj.is_valid():
            messages.error(request, "❌ OTP মেয়াদ শেষ হয়ে গেছে। আবার register করুন।")
            otpobj.delete()
            return redirect('register')

        if otpobj.otp != entered_otp:
            otpobj.attempts += 1
            otpobj.save()
            remaining = 5 - otpobj.attempts
            if remaining <= 0:
                otpobj.delete()
                messages.error(request, "❌ অনেকবার ভুল OTP দিয়েছেন। আবার register করুন।")
                return redirect('register')
            messages.error(request, f"❌ OTP ভুল হয়েছে। আরও {remaining} বার সুযোগ আছে।")
            return render(request, "htmlpages/verify.html", {'email': email})

        # ── OTP সঠিক → Account তৈরি করো ─────────────────────────
        try:
            from django.contrib.auth.hashers import is_password_usable
            user = User(
                username   = email,
                email      = email,
                first_name = otpobj.full_name,
            )
            user.password = otpobj.hashed_password  # already hashed
            user.save()

            Profile.objects.get_or_create(user=user)

            otpobj.is_used = True
            otpobj.save()

            # session পরিষ্কার করো
            if 'pending_otp_email' in request.session:
                del request.session['pending_otp_email']

            auth_login(request, user)
            messages.success(request, f"✅ স্বাগতম {otpobj.full_name}! Account সফলভাবে তৈরি হয়েছে।")
            return redirect("dashboard")

        except Exception as e:
            messages.error(request, "Account তৈরিতে সমস্যা হয়েছে। আবার চেষ্টা করুন।")
            print(f"[VaxSafe] Account creation error: {e}")
            return render(request, "htmlpages/verify.html", {'email': email})

    return render(request, "htmlpages/verify.html", {'email': email})


def resend_otp(request):
    """OTP resend।"""
    email = request.session.get('pending_otp_email')
    if not email:
        messages.error(request, "Session expired। আবার register করুন।")
        return redirect('register')

    try:
        otpobj = OTPVerification.objects.filter(
            email=email, is_used=False
        ).latest('created_at')
    except OTPVerification.DoesNotExist:
        messages.error(request, "OTP পাওয়া যায়নি। আবার register করুন।")
        return redirect('register')

    # নতুন OTP তৈরি করো
    new_otp = _generate_otp()
    otpobj.otp      = new_otp
    otpobj.attempts = 0
    otpobj.created_at = timezone.now()  # timer reset
    otpobj.save()

    sent = _send_otp_email(email, new_otp, otpobj.full_name)
    if sent:
        messages.success(request, f"✅ নতুন OTP {email} এ পাঠানো হয়েছে।")
    else:
        messages.error(request, "❌ Email পাঠাতে সমস্যা। একটু পর আবার চেষ্টা করুন।")

    return redirect('verify_otp')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        if not username or not password:
            messages.error(request, "Username এবং Password দুটোই দিতে হবে।")
            return render(request, "htmlpages/login.html")
        user = authenticate(request, username=username, password=password)
        if user is None:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        if user is not None:
            auth_login(request, user)
            messages.success(request, f"✅ স্বাগতম, {user.first_name or user.username}!")
            return redirect("dashboard")
        else:
            messages.error(request, "❌ Username/Email অথবা Password ভুল হয়েছে।")
    return render(request, "htmlpages/login.html")


def logout(request):
    auth_logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect("home")


# =====================================================
# PUBLIC PAGES
# =====================================================

def home(request):
    return render(request, "htmlpages/home.html")

def features(request):
    return render(request, "htmlpages/features.html")

def aboutUs(request):
    return render(request, "htmlpages/aboutUs.html")

def contact(request):
    return render(request, "htmlpages/contact.html")

def send_message(request):
    if request.method == 'POST':
        name    = request.POST.get('name', '')
        email   = request.POST.get('email', '')
        message = request.POST.get('message', '')
        if name and email and message:
            try:
                send_mail(
                    subject=f"New Message from {name}",
                    message=f"From: {name} ({email})\n\n{message}",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    fail_silently=False,
                )
                messages.success(request, "Thank you for contacting us!")
            except Exception as e:
                messages.error(request, "Failed to send message.")
                print(f"Email error: {e}")
        else:
            messages.error(request, "Please fill in all fields.")
        return redirect('contact')
    return redirect('home')

def verify_email(request):
    return render(request, "htmlpages/verifyemail.html")


# =====================================================
# DASHBOARD
# =====================================================

@login_required(login_url='login')
def dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    today = timezone.now().date()
    Vaccine.objects.filter(
        user=request.user, status='Scheduled', date_administered__lt=today
    ).update(status='Overdue')
    updates           = Update.objects.all().order_by("-created_at")[:5]
    total_vaccines    = Vaccine.objects.filter(user=request.user).count()
    upcoming_vaccines = Vaccine.objects.filter(
        user=request.user, status='Scheduled', date_administered__gte=today
    ).order_by('date_administered')
    overdue_count     = Vaccine.objects.filter(user=request.user, status='Overdue').count()
    active_reminders_count = VaccineReminder.objects.filter(
        user=request.user, is_sent=False, reminder_date__gte=today,
    ).count()
    family_members_count = FamilyMember.objects.filter(user=request.user).count()
    current_family = profile.current_family
    current_member = None
    group_members  = []
    user_families  = request.user.family_memberships.filter(is_active=True).select_related('family')
    if current_family:
        current_member = FamilyGroupMember.objects.filter(family=current_family, user=request.user).first()
        group_members  = FamilyGroupMember.objects.filter(family=current_family, is_active=True)
    context = {
        'updates':                updates,
        'family_members_count':   family_members_count,
        'total_vaccines':         total_vaccines,
        'upcoming_vaccines':      upcoming_vaccines[:3],
        'upcoming_count':         upcoming_vaccines.count(),
        'overdue_count':          overdue_count,
        'reminders_active':       active_reminders_count > 0,
        'active_reminders_count': active_reminders_count,
        'current_family':         current_family,
        'current_user_role':      current_member.role if current_member else None,
        'family_members':         group_members,
        'user_families':          user_families,
    }
    return render(request, "htmlpages/dashboard.html", context)


# =====================================================
# PROFILE
# =====================================================

@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        if 'delete_photo' in request.POST:
            if profile.photo:
                profile.photo.delete(save=True)
            messages.success(request, "✅ Profile photo deleted!")
            return redirect('profile')

        # ✅ user= pass করো যাতে email initial হয়
        form = ProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()

            # ✅ Email আলাদাভাবে User model এ save করো
            new_email = form.cleaned_data.get('email', '').strip()
            if new_email and new_email != request.user.email:
                # অন্য কেউ এই email ব্যবহার করছে কিনা দেখো
                if User.objects.filter(email=new_email).exclude(pk=request.user.pk).exists():
                    messages.error(request, "❌ এই Email অন্য কেউ ব্যবহার করছে।")
                    return render(request, 'htmlpages/profile.html', {
                        'form': form, 'profile': profile, 'title': 'My Profile'
                    })
                request.user.email = new_email
                request.user.save(update_fields=['email'])

            messages.success(request, "✅ Profile updated!")
            return redirect('profile')
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        # ✅ user= pass করো
        form = ProfileForm(instance=profile, user=request.user)

    return render(request, 'htmlpages/profile.html', {
        'form': form, 'profile': profile, 'title': 'My Profile'
    })

# =====================================================
# FAMILY MEMBERS
# =====================================================

@login_required
def familymembers(request):
    members = FamilyMember.objects.filter(user=request.user).annotate(vaccine_count=Count('vaccines')).order_by('name')
    return render(request, "htmlpages/familymembers.html", {
        'members': members, 'total_members': members.count(), 'title': 'Family Members'
    })


@login_required
def addfamilymember(request):
    if request.method == "POST":
        form = FamilyMemberForm(request.POST)
        if form.is_valid():
            fm = form.save(commit=False)
            fm.user = request.user
            fm.save()
            messages.success(request, f"✅ {fm.name} added!")
            return redirect("familymembers")
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        form = FamilyMemberForm()
    return render(request, "htmlpages/addfamilymember.html", {'form': form, 'title': 'Add Family Member'})


@login_required
def edit_family_member(request, member_id):
    fm = get_object_or_404(FamilyMember, id=member_id, user=request.user)
    if request.method == 'POST':
        form = FamilyMemberForm(request.POST, instance=fm)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ {fm.name} updated!')
            return redirect('familymembers')
        else:
            messages.error(request, '❌ Please correct the errors below.')
    else:
        form = FamilyMemberForm(instance=fm)
    return render(request, 'htmlpages/addfamilymember.html', {
        'form': form, 'family_member': fm, 'title': 'Edit Family Member', 'is_edit': True
    })


@login_required
def delete_family_member(request, member_id):
    fm = get_object_or_404(FamilyMember, id=member_id, user=request.user)
    if request.method == 'POST':
        name = fm.name
        fm.delete()
        messages.success(request, f'🗑️ {name} removed!')
        return redirect('familymembers')
    return render(request, 'htmlpages/delete_family_member_confirm.html', {
        'family_member': fm, 'vaccine_count': fm.vaccines.count()
    })


# =====================================================
# VACCINE MANAGEMENT  (Admin Only)
# =====================================================

@login_required
def add_vaccine(request):
    """Admin Only — যেকোনো user / সবার জন্য vaccine সেট করো + Auto Notification."""

    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "❌ টিকার রেকর্ড যোগ/সম্পাদনা করার অনুমতি নেই। শুধুমাত্র Admin এই কাজ করতে পারবেন।")
        return redirect('vaccine_schedule')

    all_users                = User.objects.all().order_by('first_name', 'username')
    user_family_members_json = _build_user_family_json(all_users)

    # ─── GET: target_user param ───────────────────────────────────────
    target_user        = request.user
    get_target_user_id = request.GET.get('target_user', '').strip()

    if get_target_user_id and get_target_user_id != 'all':
        try:
            target_user = User.objects.get(id=int(get_target_user_id))
        except (User.DoesNotExist, ValueError):
            target_user = request.user
            get_target_user_id = ''

    # ─── POST ─────────────────────────────────────────────────────────
    if request.method == 'POST':
        target_user_id = request.POST.get('target_user', '').strip()

        # ✅ "ALL USERS" case
        if target_user_id == 'all':
            form = VaccineForm(request.POST, user=request.user)
            if form.is_valid():
                active_users = User.objects.filter(is_active=True)
                count = 0
                for tu in active_users:
                    v = Vaccine(
                        user              = tu,
                        family_member     = None,   # সবার নিজের জন্য
                        name              = form.cleaned_data['name'],
                        dose_number       = form.cleaned_data['dose_number'],
                        date_administered = form.cleaned_data['date_administered'],
                        next_dose_date    = form.cleaned_data.get('next_dose_date'),
                        location          = form.cleaned_data.get('location') or '',
                        healthcare_provider = form.cleaned_data.get('healthcare_provider') or '',
                        status            = form.cleaned_data.get('status', 'Scheduled'),
                        notes             = form.cleaned_data.get('notes') or '',
                        manufacturer      = form.cleaned_data.get('manufacturer') or '',
                        batch_number      = form.cleaned_data.get('batch_number') or '',
                        side_effects      = form.cleaned_data.get('side_effects') or '',
                    )
                    v.save()
                    _send_vaccine_scheduled_notification(v, tu)
                    count += 1
                messages.success(
                    request,
                    f'✅ মোট {count} জন user এর জন্য "{form.cleaned_data["name"]}" '
                    f'({form.cleaned_data["dose_number"]}) সেট করা হয়েছে। '
                    f'সবাইকে App Notification ও Email পাঠানো হয়েছে।'
                )
                return redirect('vaccine_schedule')
            else:
                messages.error(request, '❌ Please correct the errors below.')
                return render(request, 'htmlpages/addvaccine.html', {
                    'form': form, 'title': 'টিকার রেকর্ড যোগ করুন (Admin)',
                    'is_admin': True, 'all_users': all_users,
                    'target_user': request.user,
                    'selected_target_user_id': 'all',
                    'user_family_members_json': user_family_members_json,
                })

        # ✅ SPECIFIC USER case (পুরনো logic)
        if target_user_id:
            try:
                target_user = User.objects.get(id=int(target_user_id))
            except (User.DoesNotExist, ValueError):
                target_user = request.user

        admin_family_member_id = request.POST.get('admin_family_member_id', '').strip()
        selected_family_member = None
        if admin_family_member_id:
            try:
                selected_family_member = FamilyMember.objects.get(
                    id=admin_family_member_id, user=target_user
                )
            except FamilyMember.DoesNotExist:
                selected_family_member = None

        form = VaccineForm(request.POST, user=target_user)
        if form.is_valid():
            v      = form.save(commit=False)
            v.user = target_user
            if selected_family_member:
                v.family_member = selected_family_member
            v.save()
            _send_vaccine_scheduled_notification(v, target_user)

            recipient_label = (
                selected_family_member.name
                if selected_family_member
                else (target_user.get_full_name() or target_user.username)
            )
            messages.success(
                request,
                f'✅ "{recipient_label}" এর জন্য "{v.name}" ({v.dose_number}) সেট করা হয়েছে। '
                f'App Notification ও Email পাঠানো হয়েছে।'
            )
            return redirect('vaccine_schedule')
        else:
            messages.error(request, '❌ Please correct the errors below.')

    # ─── GET ──────────────────────────────────────────────────────────
    else:
        form = VaccineForm(user=target_user)
        if get_target_user_id and get_target_user_id != 'all':
            form.fields['family_member'].queryset = FamilyMember.objects.filter(
                user=target_user
            )

    return render(request, 'htmlpages/addvaccine.html', {
        'form':                     form,
        'title':                    'টিকার রেকর্ড যোগ করুন (Admin)',
        'is_admin':                 True,
        'all_users':                all_users,
        'target_user':              target_user,
        'selected_target_user_id':  get_target_user_id,
        'user_family_members_json': user_family_members_json,
    })

@login_required
def edit_vaccine(request, vaccine_id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "❌ শুধুমাত্র Admin টিকা সম্পাদনা করতে পারবেন।")
        return redirect('vaccine_schedule')
    vaccine    = get_object_or_404(Vaccine, id=vaccine_id)
    old_status = vaccine.status
    form       = VaccineForm(request.POST or None, instance=vaccine, user=vaccine.user)
    if request.method == 'POST' and form.is_valid():
        updated = form.save()
        if old_status != 'Completed' and updated.status == 'Completed':
            _send_vaccine_completed_notification(updated)
            messages.success(request, f'✅ "{updated.name}" Completed করা হয়েছে। User কে Notification ও Email পাঠানো হয়েছে।')
        else:
            messages.success(request, f'✅ Vaccine "{updated.name}" updated!')
        return redirect('vaccine_schedule')
    elif request.method == 'POST':
        messages.error(request, '❌ Please correct the errors below.')
    return render(request, 'htmlpages/addvaccine.html', {
        'form': form, 'vaccine': vaccine, 'title': 'Edit Vaccine (Admin)', 'is_edit': True, 'is_admin': True,
    })


@login_required
def mark_vaccine_completed(request, vaccine_id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "❌ Permission denied.")
        return redirect('vaccine_schedule')
    vaccine = get_object_or_404(Vaccine, id=vaccine_id)
    if vaccine.status != 'Completed':
        vaccine.status = 'Completed'
        vaccine.save()
        _send_vaccine_completed_notification(vaccine)
        messages.success(request, f"✅ {vaccine.name} ({vaccine.dose_number}) Completed করা হয়েছে। User কে App Notification ও Email পাঠানো হয়েছে।")
    else:
        messages.info(request, "এটি ইতিমধ্যে Completed।")
    return redirect('vaccine_schedule')


@login_required
def delete_vaccine(request, vaccine_id):
    vaccine = get_object_or_404(Vaccine, id=vaccine_id, user=request.user)
    if request.method == 'POST':
        name = vaccine.name
        vaccine.delete()
        messages.success(request, f'🗑️ "{name}" deleted!')
        return redirect('vaccine_schedule')
    return render(request, 'htmlpages/delete_vaccine_confirm.html', {'vaccine': vaccine, 'title': 'Delete Vaccine'})


@login_required
def vaccine_detail(request, vaccine_id):
    vaccine = get_object_or_404(Vaccine, id=vaccine_id, user=request.user)
    return render(request, 'htmlpages/vaccine_detail.html', {
        'vaccine': vaccine, 'is_upcoming': vaccine.is_upcoming(), 'is_overdue': vaccine.is_overdue(),
        'days_until': vaccine.days_until() if vaccine.is_upcoming() else None, 'title': f'{vaccine.name} Details',
    })


@login_required
def upcoming_vaccinations(request):
    today    = timezone.now().date()
    upcoming = Vaccine.objects.filter(
        user=request.user, status='Scheduled', date_administered__gte=today
    ).select_related('family_member').order_by('date_administered')
    return render(request, 'htmlpages/upcoming_vaccinations.html', {
        'vaccinations': upcoming, 'count': upcoming.count(), 'title': 'Upcoming Vaccinations'
    })


@login_required
def overdue_vaccinations(request):
    today = timezone.now().date()
    Vaccine.objects.filter(user=request.user, status='Scheduled', date_administered__lt=today).update(status='Overdue')
    overdue = Vaccine.objects.filter(user=request.user, status='Overdue').select_related('family_member').order_by('date_administered')
    return render(request, 'htmlpages/overdue_vaccinations.html', {
        'vaccinations': overdue, 'count': overdue.count(), 'title': 'Overdue Vaccinations'
    })


@login_required
def vaccine_list(request):
    member_filter = request.GET.get('member', '')
    status_filter = request.GET.get('status', '')
    vaccines = Vaccine.objects.filter(user=request.user).select_related('family_member')
    if member_filter:
        vaccines = vaccines.filter(family_member_id=member_filter)
    if status_filter:
        vaccines = vaccines.filter(status=status_filter)
    return render(request, 'htmlpages/vaccine_list.html', {
        'vaccines': vaccines, 'family_members': FamilyMember.objects.filter(user=request.user),
        'status_choices': Vaccine.STATUS_CHOICES, 'vaccine_types': Vaccine.VACCINE_TYPES,
        'selected_member': member_filter, 'selected_status': status_filter, 'title': 'Vaccine List',
    })


# =====================================================
# VACCINE HISTORY
# =====================================================

@login_required
def vaccine_history(request, member_id=None):
    if member_id:
        member          = get_object_or_404(FamilyMember, id=member_id, user=request.user)
        vaccines        = Vaccine.objects.filter(family_member=member).order_by('-date_administered')
        member_name     = member.name
        member_relation = member.relation
    else:
        vaccines        = Vaccine.objects.filter(user=request.user, family_member__isnull=True).order_by('-date_administered')
        member_name     = request.user.get_full_name() or request.user.username
        member_relation = "Self"
    total     = vaccines.count()
    completed = vaccines.filter(status='Completed').count()
    scheduled = vaccines.filter(status='Scheduled').count()
    overdue   = vaccines.filter(status='Overdue').count()
    return render(request, 'htmlpages/vaccine_history.html', {
        'vaccines': vaccines, 'member_name': member_name, 'member_relation': member_relation,
        'total': total, 'completed_count': completed, 'scheduled_count': scheduled,
        'overdue_count': overdue, 'title': f'{member_name} — Vaccine History',
    })


# =====================================================
# REMINDERS (পুরনো Reminder model)
# =====================================================

@login_required
def add_reminder(request):
    if request.method == 'POST':
        vaccine_name       = request.POST.get('vaccine_name', '').strip()
        scheduled_datetime = request.POST.get('scheduled', '').strip()
        family_member      = request.POST.get('family_member', '').strip()
        if not (vaccine_name and scheduled_datetime and family_member):
            messages.error(request, "❌ Please fill in all required fields.")
            return redirect('reminder_list')
        try:
            Reminder.objects.create(
                user=request.user, vaccine_name=vaccine_name,
                scheduled_datetime=parse_datetime(scheduled_datetime), family_member=family_member
            )
            messages.success(request, "✅ Reminder added!")
        except Exception as e:
            messages.error(request, f"❌ Error: {str(e)}")
    return redirect('reminder_list')


@login_required
def edit_reminder(request):
    if request.method == 'POST':
        updated = 0
        for r in Reminder.objects.filter(user=request.user):
            vn   = request.POST.get(f'vaccine_name_{r.id}')
            sd   = request.POST.get(f'scheduled_{r.id}')
            fm   = request.POST.get(f'family_member_{r.id}')
            done = request.POST.get(f'completed_{r.id}') == 'on'
            if vn and sd and fm:
                try:
                    r.vaccine_name       = vn
                    r.scheduled_datetime = parse_datetime(sd)
                    r.family_member      = fm
                    r.completed          = done
                    r.save()
                    updated += 1
                except Exception as e:
                    print(f"Reminder update error {r.id}: {e}")
        if updated:
            messages.success(request, f"✅ {updated} reminder(s) updated!")
        else:
            messages.warning(request, "⚠️ No reminders updated.")
    return redirect('reminder_list')


# =====================================================
# VACCINATION CENTERS
# =====================================================

def centers(request):
    qs      = VaccinationCenter.objects.filter(is_active=True)
    q       = request.GET.get('q', '').strip()
    city    = request.GET.get('city', '').strip()
    vaccine = request.GET.get('vaccine', '').strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(address__icontains=q) | Q(city__icontains=q))
    if city:
        qs = qs.filter(city__iexact=city)
    if vaccine:
        qs = qs.filter(available_vaccines__icontains=vaccine)
    return render(request, 'htmlpages/centers.html', {
        'centers': qs, 'google_maps_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    })


def center_detail(request, center_id):
    center = get_object_or_404(VaccinationCenter, id=center_id, is_active=True)
    return render(request, 'htmlpages/center_detail.html', {
        'center': center, 'google_maps_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    })


# =====================================================
# NEWS
# =====================================================

@login_required(login_url='login')
def news_list(request):
    category_filter = request.GET.get('category', '')
    search_query    = request.GET.get('search', '')
    news_items = News.objects.filter(is_published=True)
    if category_filter:
        news_items = news_items.filter(category=category_filter)
    if search_query:
        news_items = news_items.filter(
            Q(title__icontains=search_query) | Q(summary__icontains=search_query) | Q(content__icontains=search_query)
        )
    news_items = news_items.order_by('-published_date')
    return render(request, 'htmlpages/news.html', {
        'news_items':        news_items,
        'featured_news':     News.objects.filter(is_published=True, is_featured=True).order_by('-published_date')[:3],
        'categories':        News.CATEGORY_CHOICES,
        'selected_category': category_filter,
        'search_query':      search_query,
        'total_news':        news_items.count(),
        'title':             'Health News & Updates',
    })


@login_required(login_url='login')
def news_detail(request, slug):
    news_item = get_object_or_404(News, slug=slug, is_published=True)
    news_item.increment_views()
    related = News.objects.filter(category=news_item.category, is_published=True).exclude(id=news_item.id).order_by('-published_date')[:3]
    return render(request, 'htmlpages/news_detail.html', {
        'news': news_item, 'related_news': related,
        'reading_time': news_item.get_reading_time(), 'title': news_item.title,
    })


# =====================================================
# VACCINE UPDATES
# =====================================================

@login_required(login_url='login')
def vaccine_updates(request):
    category_filter = request.GET.get('category', '')
    search_query    = request.GET.get('search', '')
    updates = VaccineUpdate.objects.filter(is_published=True)
    if category_filter:
        updates = updates.filter(category=category_filter)
    if search_query:
        updates = updates.filter(Q(title__icontains=search_query) | Q(content__icontains=search_query))
    return render(request, 'htmlpages/vaccine_updates.html', {
        'updates': updates, 'categories': VaccineUpdate.CATEGORY_CHOICES,
        'selected_category': category_filter, 'search_query': search_query, 'title': 'Vaccine Updates',
    })


@login_required(login_url='login')
def vaccine_update_detail(request, pk):
    update = get_object_or_404(VaccineUpdate, pk=pk, is_published=True)
    return render(request, 'htmlpages/vaccine_updates_detail.html', {'update': update, 'title': update.title})


@login_required(login_url='login')
def create_vaccine_update(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Permission denied.")
        return redirect('vaccine_updates')
    if request.method == 'POST':
        title    = request.POST.get('title', '').strip()
        content  = request.POST.get('content', '').strip()
        excerpt  = request.POST.get('excerpt', '').strip()
        category = request.POST.get('category', 'general')
        if title and content:
            u = VaccineUpdate.objects.create(title=title, content=content, excerpt=excerpt, category=category, author=request.user)
            messages.success(request, f'✅ "{u.title}" created!')
            return redirect('vaccine_update_detail', pk=u.pk)
        messages.error(request, '❌ Title and content required.')
    return render(request, 'htmlpages/vaccine_updates.html', {'categories': VaccineUpdate.CATEGORY_CHOICES, 'title': 'Create Vaccine Update'})


@login_required(login_url='login')
def edit_vaccine_update(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Permission denied.")
        return redirect('vaccine_updates')
    update = get_object_or_404(VaccineUpdate, pk=pk)
    if request.method == 'POST':
        update.title    = request.POST.get('title',    update.title).strip()
        update.content  = request.POST.get('content',  update.content).strip()
        update.excerpt  = request.POST.get('excerpt',  update.excerpt or '').strip()
        update.category = request.POST.get('category', update.category)
        update.save()
        messages.success(request, f'✅ "{update.title}" updated!')
        return redirect('vaccine_update_detail', pk=update.pk)
    return render(request, 'htmlpages/vaccine_updates_detail.html', {
        'update': update, 'categories': VaccineUpdate.CATEGORY_CHOICES, 'title': 'Edit Vaccine Update',
    })


# =====================================================
# FAMILY GROUP MANAGEMENT
# =====================================================

@login_required
def family_create_view(request):
    form = FamilyCreateForm(request.POST or None)
    if form.is_valid():
        family            = form.save(commit=False)
        family.created_by = request.user
        family.save()
        FamilyGroupMember.objects.create(family=family, user=request.user, role='Admin', can_view_others=True, can_edit_others=True)
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.current_family = family
        profile.save()
        messages.success(request, "Family তৈরি হয়েছে!")
        return redirect('dashboard')
    return render(request, 'htmlpages/family_create.html', {'form': form})


@login_required
def family_invite_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    family = profile.current_family
    if not family:
        messages.error(request, "আপনি কোনো family তে নেই।")
        return redirect('family_create')
    get_object_or_404(FamilyGroupMember, family=family, user=request.user, role='Admin')
    form = FamilyInviteForm(request.POST or None)
    if form.is_valid():
        invitation = FamilyInvitation.objects.create(
            family=family, invited_by=request.user,
            email=form.cleaned_data['email'], role=form.cleaned_data['role'],
            relation=form.cleaned_data['relation'], expires_at=timezone.now() + timedelta(days=7)
        )
        accept_url = request.build_absolute_uri(f'/family/accept/{invitation.token}/')
        send_mail(
            subject=f"{family.family_name} - Family Invitation",
            message=f"আপনাকে {family.family_name} তে invite করা হয়েছে।\nAccept: {accept_url}",
            from_email=settings.EMAIL_HOST_USER, recipient_list=[invitation.email]
        )
        messages.success(request, f"Invitation পাঠানো হয়েছে {invitation.email} এ!")
        return redirect('familymembers')
    return render(request, 'htmlpages/family_invite.html', {'form': form})


@login_required
def invitation_accept_view(request, token):
    invitation = get_object_or_404(FamilyInvitation, token=token)
    if not invitation.is_valid():
        messages.error(request, "Invitation expired বা আগেই use হয়েছে।")
        return redirect('dashboard')
    if request.method == 'POST':
        FamilyGroupMember.objects.get_or_create(
            family=invitation.family, user=request.user,
            defaults={'role': invitation.role, 'relation': invitation.relation}
        )
        invitation.is_accepted = True
        invitation.save()
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if not profile.current_family:
            profile.current_family = invitation.family
            profile.save()
        messages.success(request, f"{invitation.family.family_name} এ যোগ দিয়েছেন!")
        return redirect('dashboard')
    return render(request, 'htmlpages/family_accept_invite.html', {'invitation': invitation})


@login_required
def admin_transfer_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    family = profile.current_family
    if not family:
        return redirect('family_create')
    current_member = get_object_or_404(FamilyGroupMember, family=family, user=request.user, role='Admin')
    form = AdminTransferForm(family=family, current_user=request.user, data=request.POST or None)
    if form.is_valid():
        new_admin                      = form.cleaned_data['new_admin']
        current_member.role            = 'Member'
        current_member.can_edit_others = False
        current_member.save()
        new_admin.role            = 'Admin'
        new_admin.can_view_others = True
        new_admin.can_edit_others = True
        new_admin.save()
        messages.success(request, "Admin role transfer হয়েছে।")
        return redirect('familymembers')
    return render(request, 'htmlpages/admin_transfer.html', {'form': form})


@login_required
def dependent_upgrade_view(request, pk):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    family = profile.current_family
    if not family:
        return redirect('family_create')
    dep_member = get_object_or_404(FamilyGroupMember, pk=pk, family=family, role='Dependent')
    if request.method == 'POST':
        invited_email = request.POST.get('email')
        invitation = FamilyInvitation.objects.create(
            family=family, invited_by=request.user, email=invited_email, role='Member',
            relation=dep_member.relation, expires_at=timezone.now() + timedelta(days=7)
        )
        accept_url = request.build_absolute_uri(f'/family/accept/{invitation.token}/')
        send_mail(
            subject="VaxSafe - আপনার নিজস্ব account তৈরি করুন",
            message=f"Account তৈরি করুন: {accept_url}",
            from_email=settings.EMAIL_HOST_USER, recipient_list=[invited_email]
        )
        messages.success(request, "Invitation পাঠানো হয়েছে!")
        return redirect('familymembers')
    return render(request, 'htmlpages/dependent_upgrade.html', {'member': dep_member})


@login_required
def leave_family_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    family = profile.current_family
    if not family:
        return redirect('family_create')
    member = get_object_or_404(FamilyGroupMember, family=family, user=request.user)
    if member.role == 'Admin' and family.members.filter(role='Admin', is_active=True).count() == 1:
        messages.error(request, "Family ছাড়ার আগে Admin transfer করুন।")
        return redirect('familymembers')
    if request.method == 'POST':
        member.is_active = False
        member.save()
        new_family = FamilyGroup.objects.create(
            family_name=f"{request.user.first_name or request.user.username}'s Family",
            created_by=request.user
        )
        FamilyGroupMember.objects.create(family=new_family, user=request.user, role='Admin', can_view_others=True, can_edit_others=True)
        profile.current_family = new_family
        profile.save()
        messages.success(request, "Family থেকে বের হয়েছেন।")
        return redirect('dashboard')
    return render(request, 'htmlpages/leave_family.html', {'family': family})


@login_required
def switch_family_view(request, pk):
    family = get_object_or_404(FamilyGroup, pk=pk)
    get_object_or_404(FamilyGroupMember, family=family, user=request.user, is_active=True)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.current_family = family
    profile.save()
    return redirect('dashboard')


# =====================================================
# NOTIFICATION VIEWS
# =====================================================

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)
    unread_count  = notifications.filter(is_read=False).count()
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'htmlpages/notifications.html', {
        'notifications': notifications, 'unread_count': unread_count,
    })


@login_required
def delete_notification(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.delete()
    messages.success(request, "নোটিফিকেশন মুছে ফেলা হয়েছে।")
    return redirect('notification_list')


# =====================================================
# VACCINE REMINDER VIEWS
# =====================================================

@login_required
def reminder_list(request):
    if request.method == 'POST':
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "❌ শুধুমাত্র Admin Reminder সেট করতে পারবেন।")
            return redirect('reminder_list')
        return redirect('set_reminder')
    today             = timezone.now().date()
    vaccine_reminders = VaccineReminder.objects.filter(user=request.user).order_by('reminder_date')
    old_reminders     = Reminder.objects.filter(user=request.user).order_by('-scheduled_datetime')
    return render(request, 'htmlpages/reminder.html', {
        'vaccine_reminders': vaccine_reminders,
        'reminders':         old_reminders,
        'today':             today,
        'is_admin':          request.user.is_staff or request.user.is_superuser,
    })


@login_required
def set_reminder(request):
    """Admin Only — User + Family Member select করে reminder সেট।"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "❌ শুধুমাত্র Admin Reminder সেট করতে পারবেন।")
        return redirect('reminder_list')

    all_users                = User.objects.all().order_by('first_name', 'username')
    user_family_members_json = _build_user_family_json(all_users)  # ✅ shared helper use

    if request.method == 'POST':
        form = VaccineReminderForm(request.POST)

        target_user_id = request.POST.get('target_user')
        target_user    = request.user
        if target_user_id:
            try:
                target_user = User.objects.get(id=target_user_id)
            except User.DoesNotExist:
                pass

        family_member_id = request.POST.get('family_member_id')
        family_member    = None
        if family_member_id:
            try:
                family_member = FamilyMember.objects.get(id=family_member_id, user=target_user)
            except FamilyMember.DoesNotExist:
                pass

        if form.is_valid():
            vr               = form.save(commit=False)
            vr.user          = target_user
            vr.family_member = family_member
            vr.save()
            _send_reminder_notification(vr, target_user)
            recipient_label = family_member.name if family_member else (target_user.get_full_name() or target_user.username)
            messages.success(
                request,
                f"✅ '{recipient_label}' এর জন্য '{vr.vaccine_name}' রিমাইন্ডার সেট হয়েছে। "
                f"App Notification ও Email পাঠানো হয়েছে।"
            )
            return redirect('reminder_list')
        else:
            messages.error(request, "❌ তথ্য সঠিকভাবে পূরণ করুন।")
    else:
        form = VaccineReminderForm()

    return render(request, 'htmlpages/set_reminder.html', {
        'form':                     form,
        'all_users':                all_users,
        'user_family_members_json': user_family_members_json,
        'title':                    'Admin — Reminder সেট করুন',
    })


@login_required
def delete_reminder(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "❌ শুধুমাত্র Admin Reminder মুছতে পারবেন।")
        return redirect('reminder_list')
    vr = get_object_or_404(VaccineReminder, pk=pk)
    vr.delete()
    messages.success(request, "রিমাইন্ডার মুছে ফেলা হয়েছে।")
    return redirect('reminder_list')


# =====================================================
# VACCINE SCHEDULE
# =====================================================

@login_required
def vaccine_schedule(request):
    member_filter = request.GET.get('member', '')
    status_filter = request.GET.get('status', '')
    today         = timezone.now().date()
    Vaccine.objects.filter(user=request.user, status='Scheduled', date_administered__lt=today).update(status='Overdue')
    vaccines = Vaccine.objects.filter(user=request.user).select_related('family_member')
    if member_filter == 'self':
        vaccines = vaccines.filter(family_member__isnull=True)
    elif member_filter:
        vaccines = vaccines.filter(family_member_id=member_filter)
    if status_filter:
        vaccines = vaccines.filter(status=status_filter)
    context = {
        'vaccines':          vaccines,
        'upcoming_vaccines': vaccines.filter(date_administered__gte=today).order_by('date_administered'),
        'past_vaccines':     vaccines.filter(date_administered__lt=today).order_by('-date_administered'),
        'family_members':    FamilyMember.objects.filter(user=request.user),
        'total_count':       vaccines.count(),
        'upcoming_count':    vaccines.filter(date_administered__gte=today).count(),
        'completed_count':   vaccines.filter(status='Completed').count(),
        'overdue_count':     vaccines.filter(status='Overdue').count(),
        'selected_member':   member_filter,
        'selected_status':   status_filter,
        'title':             'Vaccine Schedule',
        'is_admin':          request.user.is_staff or request.user.is_superuser,
    }
    return render(request, 'htmlpages/vaccine_schedule.html', context)
