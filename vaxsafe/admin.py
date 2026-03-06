# admin.py (Only Profile Admin)

from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
  list_display = ['user', 'get_full_name', 'mobile', 'gender', 'blood_group']
list_filter = ['gender', 'blood_group']
search_fields = ['user__username', 'user__email', 'user__first_name', 'mobile']
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


# Admin Panel Title

admin.site.site_header = "VaxSafe Administration"
admin.site.site_title = "VaxSafe Admin Portal"
admin.site.index_title = "Welcome to VaxSafe Admin Panel"
