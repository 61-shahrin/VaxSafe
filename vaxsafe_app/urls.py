# urls.py (Clean Version)

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from vaxsafe import views

urlpatterns = [
    # ======================
    # ADMIN
    # ======================
    path('admin/', admin.site.urls),

    # ======================
    # PUBLIC PAGES
    # ======================
    path('', views.home, name='home'),
    path('features/', views.features, name='features'),
    path('aboutUs/', views.aboutUs, name='aboutUs'),
    path('contact/', views.contact, name='contact'),
    path('send-message/', views.send_message, name='send_message'),

    # ======================
    # AUTHENTICATION
    # ======================
    path('register/', views.register, name='register'),
    path('verify/', views.verify, name='verify'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout, name='logout'),
    path('verify-email/', views.verify_email, name='verify_email'),

    # ======================
    # DASHBOARD & PROFILE
    # ======================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
]

# ======================
# STATIC & MEDIA FILES (Development Only)
# ======================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)