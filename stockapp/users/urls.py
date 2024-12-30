""" Urls for user app"""

from django.urls import path
from .views import home, signup
urlpatterns = [
    path('', home, name='home'),
    path('user/signup/', signup, name='signup'),
]
