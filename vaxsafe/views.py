# vaxsafe/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse

# =====================================
# PUBLIC PAGES
# =====================================
def home(request):
    return render(request, 'home.html')

def features(request):
    return render(request, 'features.html')

def aboutUs(request):
    return render(request, 'aboutUs.html')

def contact(request):
    return render(request, 'contact.html')

def send_message(request):
    if request.method == "POST":
        # Placeholder: logic to save message
        return HttpResponse("Message sent successfully")
    return HttpResponse("Send message page")

# =====================================
# AUTHENTICATION
# =====================================
def register(request):
    return HttpResponse("Register Page")

def verify(request):
    return HttpResponse("OTP Verification Page")

def login_view(request):
    return HttpResponse("Login Page")

def logout(request):
    # You can call Django logout function if needed
    return HttpResponse("Logout Successful")

def verify_email(request):
    return HttpResponse("Verify Email Page")

# =====================================
# DASHBOARD & PROFILE
# =====================================
def dashboard(request):
    return HttpResponse("User Dashboard")

def profile_view(request):
    return HttpResponse("User Profile Page")

# =====================================
# FAMILY MEMBERS
# =====================================
def familymembers(request):
    return HttpResponse("List of Family Members")

def addfamilymember(request):
    return HttpResponse("Add Family Member")

def edit_family_member(request, member_id):
    return HttpResponse(f"Edit Family Member {member_id}")

def delete_family_member(request, member_id):
    return HttpResponse(f"Delete Family Member {member_id}")

# =====================================
# VACCINES
# =====================================
def add_vaccine(request):
    return HttpResponse("Add Vaccine")

def vaccine_schedule(request):
    return HttpResponse("Vaccine Schedule")

def vaccine_detail(request, vaccine_id):
    return HttpResponse(f"Vaccine Details {vaccine_id}")

def edit_vaccine(request, vaccine_id):
    return HttpResponse(f"Edit Vaccine {vaccine_id}")

def delete_vaccine(request, vaccine_id):
    return HttpResponse(f"Delete Vaccine {vaccine_id}")

def upcoming_vaccinations(request):
    return HttpResponse("Upcoming Vaccinations")

def overdue_vaccinations(request):
    return HttpResponse("Overdue Vaccinations")

# =====================================
# REMINDERS
# =====================================
def reminder(request):
    return HttpResponse("List of Reminders")

def add_reminder(request):
    return HttpResponse("Add Reminder")

def edit_reminder(request):
    return HttpResponse("Edit Reminder")

# =====================================
# VACCINATION CENTERS
# =====================================
def centers(request):
    return HttpResponse("List of Vaccination Centers")

def center_detail(request, center_id):
    return HttpResponse(f"Center Details {center_id}")

# =====================================
# NEWS & UPDATES
# =====================================
def news_list(request):
    return HttpResponse("All News Articles")

def news_detail(request, slug):
    return HttpResponse(f"News Article: {slug}")