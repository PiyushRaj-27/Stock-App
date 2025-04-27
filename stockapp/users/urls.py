""" Urls for user app"""

from django.urls import path
from .views import home, signup, profile, update_profile
urlpatterns = [
    path('', home, name='home'),
    path('user/signup/', signup, name='signup'),
    path('user/profile/', profile, name="profile"),
    path('user/profile/update',update_profile, name="user_update_profile")
]
