"""
This module contains the views for the users app.
It handles user-related actions such as login, logout, and profile management.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Customers
# Create your views here.
def home(request):
    """To handle the home page view"""
    if request.user.is_authenticated:
        return redirect("/app/dashboard")
    return render(request, 'users/home.html')

def signup(request):
    """To handle the signup page view. Never used in the project."""

    return render(request, 'users/signup.html')

@login_required(login_url="/accounts/login")
def profile(request):
    """
    To handle the profile view.
    """
    user = request.user
    username = user.username
    useremail = user.email
    credit = 0
    gender = "Male"
    nocustomer = False
    try:
        userModel = Customers.objects.filter(user = user)
        u = userModel.get(user= user)
        credit = u.credit
        gender = u.gender

    except Exception as e:
        nocustomer = True
        print("No Customer profile yet for", username, e)
        credit = 'N/A'
        gender = 'N/A'
    return render(request, 'users/profile.html', {"username": username, "usermail": useremail, "credit": credit, "gender": gender, "nocustomer": nocustomer})


@login_required(login_url="/accounts/login")
def update_profile(request):
    """
    To handle the profile update.
    """
    if request.method == "POST":
        gender = request.POST["gender"]
        isCustomer = False
        try:
            userModel = Customers.objects.get(user = request.user)
            isCustomer = True
        except Exception as e:
            pass
        print(f"Got reuqest: {gender}")
        if isCustomer:
            userModel.gender = gender
            userModel.save()
        else:
            newCustomer = Customers()
            newCustomer.gender = gender
            newCustomer.credit = 0
            newCustomer.countryCode = 'N/A'
            newCustomer.user = request.user
            newCustomer.save()
        
        return redirect('profile')

    return render(request, 'users/update_profile.html')

@login_required(login_url="/accounts/login")
def purhcase_credits(request):
    """
    To handle credits purchase requests
    """

    return render(request, "users/purchase.html")

def privacy_policy(request):
    """
    To handle privacy policy page.
    """

    return render(request, "users/privacy_policy.html", { "application_name": "Celestiya", "company_name": "Blackjak AI", "minimum_age": "18", 
                                              "x": "6", "country": "India", "email": "n8wing.017@gmail.com", "support_days": "3"
                                               })

def terms_of_service(request):
    """
    To handle terms of service page.
    """

    return render(request, 'users/tos.html', { "application_name": "Celestiya", "company_name": "Blackjak AI", "minimum_age": "18", 
                                              "x": "6", "country": "India", "email": "n8wing.017@gmail.com", "support_days": "3"
                                               })

def refund_policy(request):
    """
    To handle refund Policy page.
    """

    return render(request, 'users/refund.html', { "effective_date": "May 2025", "allow_days": "7", "application_name": "Celestiya", "company_name": "Blackjak AI", "minimum_age": "18", 
                                              "x": "6", "country": "India", "email": "n8wing.017@gmail.com", "support_days": "3"
                                               })