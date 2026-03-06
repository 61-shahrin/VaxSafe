# forms.py (Clean Version - Only Profile Form)

from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Profile

class ProfileForm(forms.ModelForm):
 """
Form for user profile management
"""


class Meta:
    model = Profile
    fields = [
        'mobile',
        'gender',
        'date_of_birth',
        'profession',
        'address',
        'blood_group',
        'photo'
    ]

    widgets = {
        'mobile': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter mobile number',
            'pattern': '[0-9+\\-\\s()]*'
        }),
        'gender': forms.Select(attrs={
            'class': 'form-control'
        }),
        'date_of_birth': forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'max': timezone.now().date().isoformat()
        }),
        'profession': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter profession'
        }),
        'address': forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter complete address'
        }),
        'blood_group': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., A+, O-, AB+',
            'pattern': '(A|B|AB|O)[+-]'
        }),
        'photo': forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
    }

    labels = {
        'mobile': 'Mobile Number',
        'gender': 'Gender',
        'date_of_birth': 'Date of Birth',
        'profession': 'Profession',
        'address': 'Address',
        'blood_group': 'Blood Group',
        'photo': 'Profile Photo'
    }

    help_texts = {
        'mobile': 'Enter your contact number',
        'date_of_birth': 'Your date of birth',
        'blood_group': 'Format: A+, O-, AB+, etc.',
        'photo': 'Upload a profile picture (optional)'
    }

def clean_mobile(self):
    """Validate mobile number"""
    mobile = self.cleaned_data.get('mobile')

    if mobile:
        cleaned = mobile.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')

        if not cleaned.isdigit():
            raise ValidationError(
                'Mobile number should contain only digits and optional +, -, (, ) characters'
            )

        if len(cleaned) < 10:
            raise ValidationError(
                'Mobile number must be at least 10 digits'
            )

    return mobile

def clean_blood_group(self):
    """Validate blood group format"""
    blood_group = self.cleaned_data.get('blood_group')

    if blood_group:
        valid_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']

        if blood_group.upper() not in valid_groups:
            raise ValidationError(
                'Please enter a valid blood group (A+, A-, B+, B-, AB+, AB-, O+, O-)'
            )

        return blood_group.upper()

    return blood_group

