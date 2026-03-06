# vaxsafe/models.py

from django.db import models
from django.contrib.auth.models import User

# =====================================================
# SYSTEM UPDATES / ANNOUNCEMENTS
# =====================================================
class Update(models.Model):
    """
    Model for system updates and announcements
    """
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Update'
        verbose_name_plural = 'Updates'

    def __str__(self):
        return self.title


# =====================================================
# USER PROFILE EXTENSION
# =====================================================
class Profile(models.Model):
    """
    Extended user profile information
    """
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other')
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    mobile = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profession = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    blood_group = models.CharField(max_length=5, blank=True, null=True)
    photo = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_full_name(self):
        """
        Return user's full name if available,
        otherwise return username
        """
        return self.user.get_full_name() or self.user.username