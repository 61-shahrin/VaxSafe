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
    Notification, VaccineReminder,
)
from .forms import (
    ProfileForm, FamilyMemberForm, VaccineForm,
    FamilyCreateForm, FamilyInviteForm, AdminTransferForm,
    VaccineReminderForm,
)


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


# =====================================================
# OTP HELPER
# =====================================================

def send_otp(request, email):
    otp = str(random.randint(100000, 999999))
    request.session['otp']      = otp
    request.session['email']    = email
    request.session['otp_time'] = time.time()
    try:
        send_mail(
            subject="Your VaxSafe Verification Code",
            message=f"Your verification code is: {otp}\n\nExpires in 5 minutes.",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        messages.error(request, "Could not send OTP. Please try again.")
        return False


# =====================================================
# AUTHENTICATION
# =====================================================

def register(request):
    if request.method == "POST":
        full_name        = request.POST.get("full_name", "").strip()
        email            = request.POST.get("email", "").strip().lower()
        password         = request.POST.get("password", "")
        confirm_password = request.POST.get("reset_password", "")

        if not all([full_name, email, password, confirm_password]):
            messages.error(request, "All fields are required.")
            return render(request, "htmlpages/register.html")
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "htmlpages/register.html")
        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return render(request, "htmlpages/register.html")
        if User.objects.filter(email=email).exists() or \
           User.objects.filter(username=email).exists():
            messages.error(request, "Email is already registered.")
            return render(request, "htmlpages/register.html")

        request.session['temp_user'] = {
            "full_name": full_name, "email": email, "password": password,
        }
        if send_otp(request, email):
            messages.info(request, "OTP sent to your email.")
            return redirect("verify")

    return render(request, "htmlpages/register.html")


def verify(request):
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "submit":
            entered_otp = request.POST.get("otp", "").strip()
            saved_otp   = request.session.get("otp")
            otp_time    = request.session.get("otp_time")

            if otp_time and time.time() - otp_time > 300:
                messages.error(request, "OTP expired. Please resend.")
                return render(request, "htmlpages/verify.html")

            if entered_otp == saved_otp:
                data = request.session.get("temp_user")
                if data:
                    try:
                        user = User.objects.create_user(
                            username=data["email"],
                            email=data["email"],
                            password=data["password"],
                            first_name=data["full_name"]
                        )
                        Profile.objects.create(user=user)
                        auth_login(request, user)
                        for key in ["otp", "otp_time", "temp_user", "email"]:
                            request.session.pop(key, None)
                        messages.success(request, "✅ Account created! Welcome to VaxSafe!")
                        return redirect("dashboard")
                    except Exception as e:
                        messages.error(request, "Error creating account. Please try again.")
                        print(f"User creation error: {e}")
            else:
                messages.error(request, "❌ Invalid OTP.")
                return render(request, "htmlpages/verify.html")

        elif action == "resend":
            email = request.session.get("email")
            if email:
                if send_otp(request, email):
                    messages.success(request, "✅ New OTP sent!")
                return render(request, "htmlpages/verify.html")
            return redirect("register")

    return render(request, "htmlpages/verify.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username or not password:
            messages.error(request, "Please provide both username and password.")
            return render(request, "htmlpages/login.html")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            messages.success(request, f"✅ Welcome back, {user.first_name or user.username}!")
            return redirect("dashboard")
        else:
            messages.error(request, "❌ Invalid username or password.")

    return render(request, "htmlpages/login.html")


def logout(request):
    auth_logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect("home")


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

    updates                = Update.objects.all().order_by("-created_at")[:5]
    total_vaccines         = Vaccine.objects.filter(user=request.user).count()
    upcoming_vaccines      = Vaccine.objects.filter(
        user=request.user, status='Scheduled', date_administered__gte=today
    ).order_by('date_administered')
    overdue_count          = Vaccine.objects.filter(user=request.user, status='Overdue').count()
    active_reminders_count = Reminder.objects.filter(
        user=request.user, completed=False, scheduled_datetime__gte=timezone.now()
    ).count()
    family_members_count   = FamilyMember.objects.filter(user=request.user).count()

    current_family = profile.current_family
    current_member = None
    group_members  = []
    user_families  = request.user.family_memberships.filter(
        is_active=True
    ).select_related('family')

    if current_family:
        current_member = FamilyGroupMember.objects.filter(
            family=current_family, user=request.user
        ).first()
        group_members = FamilyGroupMember.objects.filter(
            family=current_family, is_active=True
        )

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

        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Profile updated!")
            return redirect('profile')
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'htmlpages/profile.html', {
        'form': form, 'profile': profile, 'title': 'My Profile'
    })


# =====================================================
# FAMILY MEMBERS
# =====================================================

@login_required
def familymembers(request):
    members = FamilyMember.objects.filter(user=request.user).annotate(
        vaccine_count=Count('vaccines')
    ).order_by('name')
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
    return render(request, "htmlpages/addfamilymember.html", {
        'form': form, 'title': 'Add Family Member'
    })


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
# VACCINE MANAGEMENT
# =====================================================

@login_required
def add_vaccine(request):
    form = VaccineForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        v = form.save(commit=False)
        v.user = request.user
        v.save()
        messages.success(request, f'✅ Vaccine "{v.name}" added!')
        return redirect('vaccine_schedule')
    elif request.method == 'POST':
        messages.error(request, '❌ Please correct the errors below.')
    return render(request, 'htmlpages/addvaccine.html', {
        'form': form, 'title': 'Add Vaccine'
    })


@login_required
def vaccine_schedule(request):
    member_filter = request.GET.get('member', '')
    status_filter = request.GET.get('status', '')
    today = timezone.now().date()

    vaccines = Vaccine.objects.filter(user=request.user).select_related('family_member')
    if member_filter == 'self':
        vaccines = vaccines.filter(family_member__isnull=True)
    elif member_filter:
        vaccines = vaccines.filter(family_member_id=member_filter)
    if status_filter:
        vaccines = vaccines.filter(status=status_filter)

    Vaccine.objects.filter(
        user=request.user, status='Scheduled', date_administered__lt=today
    ).update(status='Overdue')

    context = {
        'vaccines':          vaccines,
        'upcoming_vaccines': vaccines.filter(
            date_administered__gte=today
        ).order_by('date_administered'),
        'past_vaccines':     vaccines.filter(
            date_administered__lt=today
        ).order_by('-date_administered'),
        'family_members':    FamilyMember.objects.filter(user=request.user),
        'total_count':       vaccines.count(),
        'upcoming_count':    vaccines.filter(date_administered__gte=today).count(),
        'completed_count':   vaccines.filter(status='Completed').count(),
        'overdue_count':     vaccines.filter(status='Overdue').count(),
        'selected_member':   member_filter,
        'selected_status':   status_filter,
        'title':             'Vaccine Schedule',
    }
    return render(request, 'htmlpages/vaccine_schedule.html', context)


@login_required
def edit_vaccine(request, vaccine_id):
    vaccine = get_object_or_404(Vaccine, id=vaccine_id, user=request.user)
    form = VaccineForm(request.POST or None, instance=vaccine, user=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'✅ Vaccine "{vaccine.name}" updated!')
        return redirect('vaccine_schedule')
    elif request.method == 'POST':
        messages.error(request, '❌ Please correct the errors below.')
    return render(request, 'htmlpages/addvaccine.html', {
        'form': form, 'vaccine': vaccine, 'title': 'Edit Vaccine', 'is_edit': True
    })


@login_required
def delete_vaccine(request, vaccine_id):
    vaccine = get_object_or_404(Vaccine, id=vaccine_id, user=request.user)
    if request.method == 'POST':
        name = vaccine.name
        vaccine.delete()
        messages.success(request, f'🗑️ "{name}" deleted!')
        return redirect('vaccine_schedule')
    return render(request, 'htmlpages/delete_vaccine_confirm.html', {
        'vaccine': vaccine, 'title': 'Delete Vaccine'
    })


@login_required
def vaccine_detail(request, vaccine_id):
    vaccine = get_object_or_404(Vaccine, id=vaccine_id, user=request.user)
    return render(request, 'htmlpages/vaccine_detail.html', {
        'vaccine':     vaccine,
        'is_upcoming': vaccine.is_upcoming(),
        'is_overdue':  vaccine.is_overdue(),
        'days_until':  vaccine.days_until() if vaccine.is_upcoming() else None,
        'title':       f'{vaccine.name} Details',
    })


@login_required
def upcoming_vaccinations(request):
    today    = timezone.now().date()
    upcoming = Vaccine.objects.filter(
        user=request.user, status='Scheduled', date_administered__gte=today
    ).select_related('family_member').order_by('date_administered')
    return render(request, 'htmlpages/upcoming_vaccinations.html', {
        'vaccinations': upcoming, 'count': upcoming.count(),
        'title': 'Upcoming Vaccinations'
    })


@login_required
def overdue_vaccinations(request):
    today = timezone.now().date()
    Vaccine.objects.filter(
        user=request.user, status='Scheduled', date_administered__lt=today
    ).update(status='Overdue')
    overdue = Vaccine.objects.filter(
        user=request.user, status='Overdue'
    ).select_related('family_member').order_by('date_administered')
    return render(request, 'htmlpages/overdue_vaccinations.html', {
        'vaccinations': overdue, 'count': overdue.count(),
        'title': 'Overdue Vaccinations'
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
        'vaccines':        vaccines,
        'family_members':  FamilyMember.objects.filter(user=request.user),
        'status_choices':  Vaccine.STATUS_CHOICES,
        'vaccine_types':   Vaccine.VACCINE_TYPES,
        'selected_member': member_filter,
        'selected_status': status_filter,
        'title':           'Vaccine List',
    })


# =====================================================
# REMINDERS (পুরনো Reminder model)
# =====================================================

@login_required
def reminder(request):
    reminders = Reminder.objects.filter(user=request.user).order_by('-scheduled_datetime')
    active    = [r for r in reminders if r.is_active]
    past      = [r for r in reminders if not r.is_active]
    return render(request, 'htmlpages/reminder.html', {
        'reminders':        reminders,
        'active_reminders': active,
        'past_reminders':   past,
        'active_count':     len(active),
        'title':            'Reminders',
    })


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
                user=request.user,
                vaccine_name=vaccine_name,
                scheduled_datetime=parse_datetime(scheduled_datetime),
                family_member=family_member
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
        qs = qs.filter(
            Q(name__icontains=q) | Q(address__icontains=q) | Q(city__icontains=q)
        )
    if city:
        qs = qs.filter(city__iexact=city)
    if vaccine:
        qs = qs.filter(available_vaccines__icontains=vaccine)
    return render(request, 'htmlpages/centers.html', {
        'centers':         qs,
        'google_maps_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    })


def center_detail(request, center_id):
    center = get_object_or_404(VaccinationCenter, id=center_id, is_active=True)
    return render(request, 'htmlpages/center_detail.html', {
        'center':          center,
        'google_maps_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
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
            Q(title__icontains=search_query) |
            Q(summary__icontains=search_query) |
            Q(content__icontains=search_query)
        )
    news_items = news_items.order_by('-published_date')
    return render(request, 'htmlpages/news.html', {
        'news_items':        news_items,
        'featured_news':     News.objects.filter(
            is_published=True, is_featured=True
        ).order_by('-published_date')[:3],
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
    related = News.objects.filter(
        category=news_item.category, is_published=True
    ).exclude(id=news_item.id).order_by('-published_date')[:3]
    return render(request, 'htmlpages/news_detail.html', {
        'news':         news_item,
        'related_news': related,
        'reading_time': news_item.get_reading_time(),
        'title':        news_item.title,
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
        updates = updates.filter(
            Q(title__icontains=search_query) | Q(content__icontains=search_query)
        )
    return render(request, 'htmlpages/vaccine_updates.html', {
        'updates':           updates,
        'categories':        VaccineUpdate.CATEGORY_CHOICES,
        'selected_category': category_filter,
        'search_query':      search_query,
        'title':             'Vaccine Updates',
    })


@login_required(login_url='login')
def vaccine_update_detail(request, pk):
    update = get_object_or_404(VaccineUpdate, pk=pk, is_published=True)
    return render(request, 'htmlpages/vaccine_updates_detail.html', {
        'update': update, 'title': update.title
    })


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
            u = VaccineUpdate.objects.create(
                title=title, content=content, excerpt=excerpt,
                category=category, author=request.user,
            )
            messages.success(request, f'✅ "{u.title}" created!')
            return redirect('vaccine_update_detail', pk=u.pk)
        messages.error(request, '❌ Title and content required.')
    return render(request, 'htmlpages/vaccine_updates.html', {
        'categories': VaccineUpdate.CATEGORY_CHOICES,
        'title':      'Create Vaccine Update',
    })


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
        'update':     update,
        'categories': VaccineUpdate.CATEGORY_CHOICES,
        'title':      'Edit Vaccine Update',
    })


# =====================================================
# UTILITY
# =====================================================

def verify_email(request):
    return render(request, "htmlpages/verifyemail.html")


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
        FamilyGroupMember.objects.create(
            family=family, user=request.user,
            role='Admin', can_view_others=True, can_edit_others=True
        )
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
            family=family,
            invited_by=request.user,
            email=form.cleaned_data['email'],
            role=form.cleaned_data['role'],
            relation=form.cleaned_data['relation'],
            expires_at=timezone.now() + timedelta(days=7)
        )
        accept_url = request.build_absolute_uri(f'/family/accept/{invitation.token}/')
        send_mail(
            subject=f"{family.family_name} - Family Invitation",
            message=(
                f"আপনাকে {family.family_name} তে invite করা হয়েছে।\n"
                f"Accept: {accept_url}"
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[invitation.email]
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

    current_member = get_object_or_404(
        FamilyGroupMember, family=family, user=request.user, role='Admin'
    )
    form = AdminTransferForm(
        family=family, current_user=request.user, data=request.POST or None
    )
    if form.is_valid():
        new_admin                    = form.cleaned_data['new_admin']
        current_member.role          = 'Member'
        current_member.can_edit_others = False
        current_member.save()
        new_admin.role               = 'Admin'
        new_admin.can_view_others    = True
        new_admin.can_edit_others    = True
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

    dep_member = get_object_or_404(
        FamilyGroupMember, pk=pk, family=family, role='Dependent'
    )
    if request.method == 'POST':
        invited_email = request.POST.get('email')
        invitation = FamilyInvitation.objects.create(
            family=family, invited_by=request.user,
            email=invited_email, role='Member',
            relation=dep_member.relation,
            expires_at=timezone.now() + timedelta(days=7)
        )
        accept_url = request.build_absolute_uri(f'/family/accept/{invitation.token}/')
        send_mail(
            subject="VaxSafe - আপনার নিজস্ব account তৈরি করুন",
            message=f"Account তৈরি করুন: {accept_url}",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[invited_email]
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

    if member.role == 'Admin' and \
       family.members.filter(role='Admin', is_active=True).count() == 1:
        messages.error(request, "Family ছাড়ার আগে Admin transfer করুন।")
        return redirect('familymembers')

    if request.method == 'POST':
        member.is_active = False
        member.save()
        new_family = FamilyGroup.objects.create(
            family_name=f"{request.user.first_name or request.user.username}'s Family",
            created_by=request.user
        )
        FamilyGroupMember.objects.create(
            family=new_family, user=request.user,
            role='Admin', can_view_others=True, can_edit_others=True
        )
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
        'notifications': notifications,
        'unread_count':  unread_count,
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
def set_reminder(request):
    if request.method == 'POST':
        form = VaccineReminderForm(request.POST)
        if form.is_valid():
            vr      = form.save(commit=False)
            vr.user = request.user
            vr.save()
            Notification.objects.create(
                user=request.user,
                title="নতুন রিমাইন্ডার সেট হয়েছে ✅",
                message=(
                    f"'{vr.vaccine_name}' ভ্যাকসিনের রিমাইন্ডার "
                    f"{vr.reminder_date} তারিখে সেট করা হয়েছে।"
                ),
                notif_type='reminder'
            )
            messages.success(request, "রিমাইন্ডার সফলভাবে সেট হয়েছে!")
            return redirect('reminder_list')
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        form = VaccineReminderForm()
    return render(request, 'htmlpages/reminder.html', {'form': form})


@login_required
def reminder_list(request):
    vaccine_reminders = VaccineReminder.objects.filter(
        user=request.user
    ).order_by('reminder_date')
    old_reminders = Reminder.objects.filter(
        user=request.user
    ).order_by('-scheduled_datetime')
    today = timezone.now().date()
    return render(request, 'htmlpages/reminder.html', {
        'vaccine_reminders': vaccine_reminders,
        'reminders':         old_reminders,
        'today':             today,
        'form':              VaccineReminderForm(),
    })


@login_required
def delete_reminder(request, pk):
    vr = get_object_or_404(VaccineReminder, pk=pk, user=request.user)
    vr.delete()
    messages.success(request, "রিমাইন্ডার মুছে ফেলা হয়েছে।")
    return redirect('reminder_list')

def reminder(request):
    return render(request, 'htmlpages/reminder.html')
