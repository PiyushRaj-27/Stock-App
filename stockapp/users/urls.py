from django.contrib import admin
from django.urls import path, include
from .views import home, signup
urlpatterns = [
    path('', home, name='home'),
    path('user/signup/', signup, name='signup'),
]
