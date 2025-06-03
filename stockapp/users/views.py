"""
This module contains the views for the users app.
It handles user-related actions such as login, logout, and profile management.
"""

from datetime import datetime
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import Customers
from .models import Purchase
from django.core.exceptions import ObjectDoesNotExist
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

@csrf_exempt
def gumroad_ping(request):
    """
    To handle gumroad ping.
    """

    # gumroad only sends POST Request
    if request.method == 'POST':
        try:
            data = request.POST

            # custom field contain the real user EMAIL ID
            # real lable: Email ID (Enter the same Email ID with which you have registered on BlacJak)
            custom_fields = json.loads(data.get('custom_fields', '{}'))
            custom_email = custom_fields.get('Email ID', "")


            try:
                user = User.objects.get(email=custom_email)
                customer = Customers.objects.get(user=user)


            except (ObjectDoesNotExist):
                customer = None
            # first create a purchase reacord. Very important incase if user accidently fumbled and did not provide correct email and stuff
            purchase = Purchase.objects.create(
                customer=customer,
                sale_id=data.get('sale_id'),
                sale_timestamp=datetime.fromisoformat(data.get('sale_timestamp')),
                order_number=data.get('order_number'),
                product_id=data.get('product_id'),
                product_permalink=data.get('product_permalink'),
                short_product_id=data.get('short_product_id'),
                product_name=data.get('product_name'),
                full_name=data.get('full_name', ''),
                price_cents=int(data.get('price', 0)),
                quantity=int(data.get('quantity', 1)),
                ip_country=data.get('ip_country', ''),
                affiliate_email=data.get('affiliate', ''),
                refunded=data.get('refunded', 'false') == 'true',
                custom_email_id=custom_email
            )
            purchase.save()

            if not custom_email or custom_email == "":
                return JsonResponse({'status': 'error', 'message': 'Custom Email ID not provided'}, status=400)

            product_name = data.get('product_name', '')
            if product_name.strip().lower() == "blacjak - 99" and customer:
                customer.credit += 10 * int(data.get('quantity', 1))
                customer.save()

            return JsonResponse({'status': 'success'},status=200)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'invalid method'}, status=405)