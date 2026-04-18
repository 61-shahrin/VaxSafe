# admin.py — VaxSafe (Full Updated)
from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.core.mail import send_mail
from django.conf import settings

from .models import (
    Update, Profile, FamilyMember, Vaccine, Reminder,
    VaccinationCenter, News, VaccineUpdate,
    Notification, VaccineReminder,
    VaccineSchedule, CustomVaccineType,
)

# =====================================================================
# 🔔  MODULE-LEVEL NOTIFICATION HELPERS
# =====================================================================

def _notify(user, title, msg, notif_type='reminder', send_email=True):
    """App Notification তৈরি করো + Email পাঠাও।"""
    Notification.objects.create(
        user=user, title=title, message=msg, notif_type=notif_type
    )
    if send_email and user.email:
        try:
            send_mail(
                subject=f"VaxSafe — {title}",
                message=f"{title}\n\n{msg}\n\n---\nVaxSafe Vaccination Management",
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@vaxsafe.com'),
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"[VaxSafe Admin] Email error: {e}")


# =====================================================================
# UPDATE ADMIN
# =====================================================================

@admin.register(Update)
class UpdateAdmin(admin.ModelAdmin):
    list_display    = ['title', 'posted_by', 'created_at']
    list_filter     = ['created_at', 'posted_by']
    search_fields   = ['title', 'description']
    date_hierarchy  = 'created_at'
    readonly_fields = ['created_at']

    fieldsets = (
        ('Update Information', {
            'fields': ('title', 'description', 'posted_by')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


# =====================================================================
# PROFILE ADMIN
# =====================================================================

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display    = ['user', 'get_full_name', 'mobile', 'gender', 'blood_group']
    list_filter     = ['gender', 'blood_group']
    search_fields   = ['user__username', 'user__email', 'user__first_name', 'mobile']
    readonly_fields = ['user']

    fieldsets = (
        ('User Account',          {'fields': ('user',)}),
        ('Personal Information',  {'fields': ('mobile', 'gender', 'date_of_birth', 'blood_group')}),
        ('Professional',          {'fields': ('profession', 'address')}),
        ('Profile Photo',         {'fields': ('photo',)}),
    )

    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'


# =====================================================================
# FAMILY MEMBER ADMIN
# =====================================================================

@admin.register(FamilyMember)
class FamilyMemberAdmin(admin.ModelAdmin):
    list_display    = ['name', 'relation', 'user', 'age', 'gender', 'blood_group', 'vaccine_count_display']
    list_filter     = ['relation', 'gender', 'blood_group']
    search_fields   = ['name', 'user__username']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Family Member Information', {'fields': ('user', 'name', 'relation')}),
        ('Personal Details',          {'fields': ('age', 'date_of_birth', 'gender', 'blood_group')}),
        ('Legacy Fields',             {'fields': ('vaccine_name', 'date_time', 'notification_type'), 'classes': ('collapse',)}),
        ('Metadata',                  {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def vaccine_count_display(self, obj):
        count = obj.vaccines.count()
        if count > 0:
            return format_html('<span style="color:green;font-weight:bold;">{} vaccines</span>', count)
        return format_html('<span style="color:gray;">No vaccines</span>')
    vaccine_count_display.short_description = 'Vaccines'


# =====================================================================
# VACCINE ADMIN  ← 🔔 MAJOR CHANGE: save_model এ auto-notification
# =====================================================================

def _build_vaccine_completed_msg(vaccine):
    recipient_name = vaccine.get_recipient_name()
    lines = [
        f"অভিনন্দন! {recipient_name} এর {vaccine.name} ({vaccine.dose_number})",
        "টিকা সফলভাবে সম্পন্ন হয়েছে।",
    ]
    if vaccine.next_dose_date:
        lines += [
            "",
            f"📅 পরবর্তী ডোজ: {vaccine.next_dose_date.strftime('%d %B %Y')}",
            "অনুগ্রহ করে এই তারিখে টিকা নিতে ভুলবেন না।",
        ]
    else:
        lines.append("\n🎉 এটি এই টিকার সর্বশেষ ডোজ ছিল।")
    return "\n".join(lines)


@admin.register(Vaccine)
class VaccineAdmin(admin.ModelAdmin):
    list_display    = ['name', 'dose_number', 'get_recipient', 'date_administered',
                       'status_badge', 'user', 'next_dose_date']
    list_filter     = ['name', 'status', 'dose_number', 'date_administered']
    search_fields   = ['name', 'user__username', 'family_member__name', 'manufacturer', 'location']
    date_hierarchy  = 'date_administered'
    readonly_fields = ['created_at', 'updated_at']
    actions         = ['action_mark_completed']

    fieldsets = (
        ('Vaccine Information',  {'fields': ('user', 'family_member', 'name', 'dose_number', 'manufacturer', 'batch_number')}),
        ('Date Information',     {'fields': ('date_administered', 'next_dose_date', 'status')}),
        ('Location & Provider',  {'fields': ('location', 'healthcare_provider')}),
        ('Notes & Side Effects', {'fields': ('notes', 'side_effects'), 'classes': ('collapse',)}),
        ('Metadata',             {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    # ------------------------------------------------------------------
    # 🔔  AUTO NOTIFICATION ON SAVE
    # ------------------------------------------------------------------

    def save_model(self, request, obj, form, change):
        is_new = not change
        old_status = None
        if change and obj.pk:
            try:
                old_status = Vaccine.objects.get(pk=obj.pk).status
            except Vaccine.DoesNotExist:
                pass
        super().save_model(request, obj, form, change)
        if is_new:
            recipient = obj.get_recipient_name()
            title = f"💉 {obj.name} — {obj.dose_number} নির্ধারিত"
            msg_lines = [
                f"Admin আপনার / পরিবারের সদস্য ({recipient}) এর জন্য",
                f"{obj.name} ({obj.dose_number}) টিকা নির্ধারণ করেছেন।",
                f"📅 তারিখ: {obj.date_administered.strftime('%d %B %Y')}",
            ]
            if obj.next_dose_date:
                msg_lines.append(f"📌 পরবর্তী ডোজ: {obj.next_dose_date.strftime('%d %B %Y')}")
            if obj.location:
                msg_lines.append(f"📍 স্থান: {obj.location}")
            _notify(obj.user, title, "\n".join(msg_lines), notif_type='reminder')
            self.message_user(request, f"✅ '{obj.name}' সেট হয়েছে। {obj.user.username} কে Notification পাঠানো হয়েছে।")
        elif old_status and old_status != 'Completed' and obj.status == 'Completed':
            title = f"✅ {obj.name} — {obj.dose_number} সম্পন্ন!"
            msg   = _build_vaccine_completed_msg(obj)
            _notify(obj.user, title, msg, notif_type='update')
            self.message_user(request, f"✅ '{obj.name}' Completed। {obj.user.username} কে Notification পাঠানো হয়েছে।")

    # ------------------------------------------------------------------
    # 🔔  BULK ACTION: Mark Selected Completed
    # ------------------------------------------------------------------

    @admin.action(description='✅ Selected vaccines → Completed করো ও Notification পাঠাও')
    def action_mark_completed(self, request, queryset):
        updated = 0
        for vaccine in queryset:
            if vaccine.status != 'Completed':
                vaccine.status = 'Completed'
                vaccine.save()
                title = f"✅ {vaccine.name} — {vaccine.dose_number} সম্পন্ন!"
                msg   = _build_vaccine_completed_msg(vaccine)
                _notify(vaccine.user, title, msg, notif_type='update')
                updated += 1
        self.message_user(
            request,
            f"✅ {updated} টি vaccine Completed করা হয়েছে। "
            f"সকল user কে Notification ও Email পাঠানো হয়েছে।"
        )

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def get_recipient(self, obj):
        return obj.get_recipient_name()
    get_recipient.short_description = 'Recipient'

    def status_badge(self, obj):
        colors = {
            'Scheduled': 'blue', 'Completed': 'green',
            'Overdue': 'red',    'Cancelled': 'gray',
        }
        return format_html(
            '<span style="color:{};font-weight:bold;">{}</span>',
            colors.get(obj.status, 'black'), obj.status
        )
    status_badge.short_description = 'Status'


# =====================================================================
# REMINDER ADMIN
# =====================================================================

@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display    = ['vaccine_name', 'family_member', 'user', 'scheduled_datetime', 'status_badge', 'completed']
    list_filter     = ['completed', 'scheduled_datetime']
    search_fields   = ['vaccine_name', 'family_member', 'user__username']
    date_hierarchy  = 'scheduled_datetime'
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Reminder Information', {'fields': ('user', 'vaccine_name', 'family_member')}),
        ('Schedule',             {'fields': ('scheduled_datetime', 'completed')}),
        ('Metadata',             {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def status_badge(self, obj):
        colors = {'Active': 'green', 'Completed': 'blue', 'Missed': 'red'}
        return format_html(
            '<span style="color:{};font-weight:bold;">{}</span>',
            colors.get(obj.status, 'black'), obj.status
        )
    status_badge.short_description = 'Status'


# =====================================================================
# VACCINATION CENTER ADMIN
# =====================================================================

@admin.register(VaccinationCenter)
class VaccinationCenterAdmin(admin.ModelAdmin):
    list_display    = ['name', 'city', 'phone', 'active_status', 'is_verified', 'rating', 'created_at']
    list_filter     = ['city', 'is_active', 'is_verified', 'created_at']
    search_fields   = ['name', 'address', 'available_vaccines', 'phone', 'email']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy  = 'created_at'

    fieldsets = (
        ('Center Information',      {'fields': ('name', 'address', 'city', 'is_active', 'is_verified', 'rating')}),
        ('Contact Information',     {'fields': ('phone', 'email')}),
        ('Operating Hours',         {'fields': ('opening_time', 'closing_time')}),
        ('Services',                {'fields': ('available_vaccines', 'description')}),
        ('Location (Google Maps)',  {'fields': ('latitude', 'longitude', 'website'), 'classes': ('collapse',)}),
        ('Metadata',                {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def active_status(self, obj):
        if obj.is_active:
            return format_html('<span style="color:green;font-weight:bold;">✓ Active</span>')
        return format_html('<span style="color:red;font-weight:bold;">✗ Inactive</span>')
    active_status.short_description = 'Status'


# =====================================================================
# NEWS ADMIN
# =====================================================================

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display        = ['title', 'category', 'published_status', 'featured_badge', 'views', 'published_date']
    list_filter         = ['category', 'is_published', 'is_featured', 'published_date']
    search_fields       = ['title', 'content', 'summary', 'source']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields     = ['views', 'created_at', 'updated_at']
    date_hierarchy      = 'published_date'

    fieldsets = (
        ('Article Information', {'fields': ('title', 'slug', 'category', 'author')}),
        ('Content',             {'fields': ('summary', 'content', 'image')}),
        ('Source',              {'fields': ('source', 'source_url'), 'classes': ('collapse',)}),
        ('Publishing',          {'fields': ('is_published', 'is_featured', 'published_date')}),
        ('Statistics',          {'fields': ('views',), 'classes': ('collapse',)}),
        ('Metadata',            {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def published_status(self, obj):
        if obj.is_published:
            return format_html('<span style="color:green;font-weight:bold;">✓ Published</span>')
        return format_html('<span style="color:orange;font-weight:bold;">✎ Draft</span>')
    published_status.short_description = 'Published'

    def featured_badge(self, obj):
        if obj.is_featured:
            return format_html('<span style="color:goldenrod;font-weight:bold;">★ Featured</span>')
        return '-'
    featured_badge.short_description = 'Featured'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
        super().save_model(request, obj, form, change)


# =====================================================================
# VACCINE UPDATE ADMIN
# =====================================================================

@admin.register(VaccineUpdate)
class VaccineUpdateAdmin(admin.ModelAdmin):
    list_display    = ['title', 'category', 'author', 'is_published', 'date']
    list_filter     = ['category', 'is_published', 'date']
    search_fields   = ['title', 'content']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy  = 'date'

    fieldsets = (
        ('Content',    {'fields': ('title', 'content', 'excerpt', 'category', 'author')}),
        ('Publishing', {'fields': ('is_published', 'date')}),
        ('Metadata',   {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def save_model(self, request, obj, form, change):
        if not change and not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)


# =====================================================================
# NOTIFICATION ADMIN
# =====================================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display    = ['user', 'title', 'notif_type', 'is_read', 'created_at']
    list_filter     = ['notif_type', 'is_read', 'created_at']
    search_fields   = ['user__username', 'title', 'message']
    readonly_fields = ['created_at']
    actions         = ['mark_all_read']

    fieldsets = (
        ('Notification Info', {'fields': ('user', 'title', 'message', 'notif_type')}),
        ('Status',            {'fields': ('is_read',)}),
        ('Metadata',          {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    @admin.action(description='Mark selected notifications as Read')
    def mark_all_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, "Selected notifications marked as read.")


# =====================================================================
# VACCINE REMINDER ADMIN  ← 🔔 MAJOR CHANGE: save_model এ auto-notification
# =====================================================================

@admin.register(VaccineReminder)
class VaccineReminderAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_recipient_display', 'vaccine_name',
                    'reminder_date', 'reminder_time', 'is_sent', 'created_at']
    list_filter  = ['is_sent', 'reminder_date']
    search_fields = ['user__username', 'vaccine_name', 'family_member__name']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Reminder Info', {
            'fields': ('user', 'family_member', 'vaccine_name',
                       'reminder_date', 'reminder_time', 'note')
        }),
        ('Status',   {'fields': ('is_sent',)}),
        ('Metadata', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.user_id:
            form.base_fields['family_member'].queryset = (
                form.base_fields['family_member'].queryset.filter(user=obj.user)
            )
        return form

    def get_recipient_display(self, obj):
        name = obj.get_recipient_name()
        if obj.family_member:
            return format_html(
                '<span style="color:#0984e3;font-weight:bold;">👨‍👩‍👧 {}</span>', name
            )
        return format_html('<span style="color:#636e72;">👤 {} (Self)</span>', name)
    get_recipient_display.short_description = 'Recipient'


# =====================================================================
# VACCINE SCHEDULE ADMIN  (Admin-only)
# =====================================================================

@admin.register(VaccineSchedule)
class VaccineScheduleAdmin(admin.ModelAdmin):
    list_display    = ['vaccine_name', 'dose_number', 'interval_days_display', 'is_active', 'created_by']
    list_filter     = ['vaccine_name', 'is_active']
    search_fields   = ['vaccine_name', 'description']
    readonly_fields = ['created_at']

    fieldsets = (
        ('ভ্যাকসিন তথ্য', {'fields': ('vaccine_name', 'dose_number', 'interval_days', 'description', 'is_active')}),
        ('Metadata',        {'fields': ('created_by', 'created_at'), 'classes': ('collapse',)}),
    )

    def interval_days_display(self, obj):
        if obj.interval_days == 0:
            return format_html('<span style="color:gray;">শেষ ডোজ</span>')
        return format_html(
            '<span style="color:blue;font-weight:bold;">{} দিন পর</span>', obj.interval_days
        )
    interval_days_display.short_description = 'পরের ডোজ'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# =====================================================================
# ADMIN SITE CUSTOMIZATION
# =====================================================================
admin.site.site_header = "VaxSafe Administration"
admin.site.site_title  = "VaxSafe Admin Portal"
admin.site.index_title = "Welcome to VaxSafe Admin Panel"
