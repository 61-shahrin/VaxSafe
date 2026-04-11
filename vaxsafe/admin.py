# admin.py - Fixed & Clean for VaxSafe
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Update,
    Profile,
    FamilyMember,
    Vaccine,
    Reminder,
    VaccinationCenter,
    News,
    VaccineUpdate,
    Notification,
    VaccineReminder,
)


# =====================================================
# UPDATE ADMIN
# =====================================================
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


# =====================================================
# PROFILE ADMIN
# =====================================================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display    = ['user', 'get_full_name', 'mobile', 'gender', 'blood_group']
    list_filter     = ['gender', 'blood_group']
    search_fields   = ['user__username', 'user__email', 'user__first_name', 'mobile']
    readonly_fields = ['user']

    fieldsets = (
        ('User Account', {
            'fields': ('user',)
        }),
        ('Personal Information', {
            'fields': ('mobile', 'gender', 'date_of_birth', 'blood_group')
        }),
        ('Professional Information', {
            'fields': ('profession', 'address')
        }),
        ('Profile Photo', {
            'fields': ('photo',)
        }),
    )

    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'


# =====================================================
# FAMILY MEMBER ADMIN
# =====================================================
@admin.register(FamilyMember)
class FamilyMemberAdmin(admin.ModelAdmin):
    list_display    = ['name', 'user', 'relation', 'display_age', 'gender', 'blood_group', 'vaccine_count_display']
    list_filter     = ['relation', 'gender', 'blood_group']
    search_fields   = ['name', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy  = 'created_at'

    fieldsets = (
        ('Family Member Information', {
            'fields': ('user', 'name', 'relation')
        }),
        ('Personal Details', {
            'fields': ('age', 'date_of_birth', 'gender', 'blood_group')
        }),
        ('Legacy Fields', {
            'fields': ('vaccine_name', 'date_time', 'notification_type'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def vaccine_count_display(self, obj):
        count = obj.vaccines.count()
        if count > 0:
            return format_html(
                '<span style="color:green; font-weight:bold;">{} vaccines</span>', count
            )
        return format_html('<span style="color:gray;">No vaccines</span>')
    vaccine_count_display.short_description = 'Vaccines'


# =====================================================
# VACCINE ADMIN
# =====================================================
@admin.register(Vaccine)
class VaccineAdmin(admin.ModelAdmin):
    list_display    = ['name', 'dose_number', 'get_recipient', 'date_administered', 'status_badge', 'user']
    list_filter     = ['name', 'status', 'dose_number', 'date_administered']
    search_fields   = ['name', 'user__username', 'family_member__name', 'manufacturer', 'location']
    date_hierarchy  = 'date_administered'
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Vaccine Information', {
            'fields': ('user', 'family_member', 'name', 'dose_number', 'manufacturer', 'batch_number')
        }),
        ('Date Information', {
            'fields': ('date_administered', 'next_dose_date', 'status')
        }),
        ('Location & Provider', {
            'fields': ('location', 'healthcare_provider')
        }),
        ('Notes & Side Effects', {
            'fields': ('notes', 'side_effects'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_recipient(self, obj):
        return obj.get_recipient_name()
    get_recipient.short_description = 'Recipient'

    def status_badge(self, obj):
        colors = {
            'Scheduled': 'blue',
            'Completed': 'green',
            'Overdue':   'red',
            'Cancelled': 'gray',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>', color, obj.status
        )
    status_badge.short_description = 'Status'


# =====================================================
# REMINDER ADMIN  (পুরনো model)
# =====================================================
@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display    = ['vaccine_name', 'family_member', 'user', 'scheduled_datetime', 'status_badge', 'completed']
    list_filter     = ['completed', 'scheduled_datetime']
    search_fields   = ['vaccine_name', 'family_member', 'user__username']
    date_hierarchy  = 'scheduled_datetime'
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Reminder Information', {
            'fields': ('user', 'vaccine_name', 'family_member')
        }),
        ('Schedule', {
            'fields': ('scheduled_datetime', 'completed')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        colors = {'Active': 'green', 'Completed': 'blue', 'Missed': 'red'}
        color  = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>', color, obj.status
        )
    status_badge.short_description = 'Status'


# =====================================================
# VACCINATION CENTER ADMIN
# =====================================================
@admin.register(VaccinationCenter)
class VaccinationCenterAdmin(admin.ModelAdmin):
    list_display    = ['name', 'city', 'phone', 'active_status', 'is_verified', 'rating', 'created_at']
    list_filter     = ['city', 'is_active', 'is_verified', 'created_at']
    search_fields   = ['name', 'address', 'available_vaccines', 'phone', 'email']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy  = 'created_at'

    fieldsets = (
        ('Center Information', {
            'fields': ('name', 'address', 'city', 'is_active', 'is_verified', 'rating')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email')
        }),
        ('Operating Hours', {
            'fields': ('opening_time', 'closing_time')
        }),
        ('Services', {
            'fields': ('available_vaccines', 'description')
        }),
        ('Location (Google Maps)', {
            'fields': ('latitude', 'longitude', 'website'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def active_status(self, obj):
        if obj.is_active:
            return format_html('<span style="color:green; font-weight:bold;">✓ Active</span>')
        return format_html('<span style="color:red; font-weight:bold;">✗ Inactive</span>')
    active_status.short_description = 'Status'

    # ✅ geocode_address সরিয়ে ফেলা হয়েছে — models এ নেই
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)


# =====================================================
# NEWS ADMIN
# =====================================================
@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display        = ['title', 'category', 'published_status', 'featured_badge', 'views', 'published_date']
    list_filter         = ['category', 'is_published', 'is_featured', 'published_date']
    search_fields       = ['title', 'content', 'summary', 'source']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields     = ['views', 'created_at', 'updated_at']
    date_hierarchy      = 'published_date'

    fieldsets = (
        ('Article Information', {
            'fields': ('title', 'slug', 'category', 'author')
        }),
        ('Content', {
            'fields': ('summary', 'content', 'image')
        }),
        ('Source & Attribution', {
            'fields': ('source', 'source_url'),
            'classes': ('collapse',)
        }),
        ('Publishing', {
            'fields': ('is_published', 'is_featured', 'published_date')
        }),
        ('Statistics', {
            'fields': ('views',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def published_status(self, obj):
        if obj.is_published:
            return format_html('<span style="color:green; font-weight:bold;">✓ Published</span>')
        return format_html('<span style="color:orange; font-weight:bold;">✎ Draft</span>')
    published_status.short_description = 'Published'

    def featured_badge(self, obj):
        if obj.is_featured:
            return format_html('<span style="color:goldenrod; font-weight:bold;">★ Featured</span>')
        return '-'
    featured_badge.short_description = 'Featured'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
        super().save_model(request, obj, form, change)


# =====================================================
# VACCINE UPDATE ADMIN
# =====================================================
@admin.register(VaccineUpdate)
class VaccineUpdateAdmin(admin.ModelAdmin):
    list_display    = ['title', 'category', 'author', 'is_published', 'date']
    list_filter     = ['category', 'is_published', 'date']
    search_fields   = ['title', 'content']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy  = 'date'

    fieldsets = (
        ('Content', {
            'fields': ('title', 'content', 'excerpt', 'category', 'author')
        }),
        ('Publishing', {
            'fields': ('is_published', 'date')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change and not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)


# =====================================================
# NOTIFICATION ADMIN
# =====================================================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display    = ['user', 'title', 'notif_type', 'is_read', 'created_at']
    list_filter     = ['notif_type', 'is_read', 'created_at']
    search_fields   = ['user__username', 'title', 'message']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Notification Info', {
            'fields': ('user', 'title', 'message', 'notif_type')
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


# =====================================================
# VACCINE REMINDER ADMIN
# =====================================================
@admin.register(VaccineReminder)
class VaccineReminderAdmin(admin.ModelAdmin):
    list_display    = ['user', 'vaccine_name', 'reminder_date', 'reminder_time', 'is_sent', 'created_at']
    list_filter     = ['is_sent', 'reminder_date']
    search_fields   = ['user__username', 'vaccine_name']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Reminder Info', {
            'fields': ('user', 'vaccine_name', 'reminder_date', 'reminder_time', 'note')
        }),
        ('Status', {
            'fields': ('is_sent',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


# =====================================================
# ADMIN SITE CUSTOMIZATION
# =====================================================
admin.site.site_header = "VaxSafe Administration"
admin.site.site_title  = "VaxSafe Admin Portal"
admin.site.index_title = "Welcome to VaxSafe Admin Panel"
