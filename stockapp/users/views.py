"""
This module contains the views for the users app.
It handles user-related actions such as login, logout, and profile management.
"""

from django.shortcuts import render, redirect

# Create your views here.
def home(request):
    """To handle the home page view"""
    if request.user.is_authenticated:
        return redirect("/app/dashboard")
    return render(request, 'users/home.html')

def signup(request):
    """To handle the signup page view. Never used in the project."""

    return render(request, 'users/signup.html')
