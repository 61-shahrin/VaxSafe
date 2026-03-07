# vaxsafe/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse


# =====================================
# PUBLIC PAGES
# =====================================

def home(request):
    return render(request, 'htmlpages/home.html')


def features(request):
    return render(request, 'htmlpages/features.html')


def aboutUs(request):
    return render(request, 'htmlpages/aboutUs.html')


def contact(request):
    return render(request, 'htmlpages/contact.html')


def send_message(request):
    if request.method == "POST":
        return HttpResponse("Message sent successfully")
    return HttpResponse("Send message page")


# =====================================
# AUTHENTICATION
# =====================================

def register(request):
    return render(request, 'htmlpages/register.html')


def verify(request):
    return render(request, 'htmlpages/verify.html')


def login_view(request):
    return render(request, 'htmlpages/login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


def verify_email(request):
    return render(request, 'htmlpages/verify.html')


# =====================================
# PROFILE PAGE
# =====================================

def profile_view(request):
    return render(request, 'htmlpages/profile.html')
