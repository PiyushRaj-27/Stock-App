""" Urls for user app"""

from django.urls import path
from .views import home, signup, profile, update_profile, purhcase_credits, privacy_policy, terms_of_service, refund_policy, gumroad_ping
urlpatterns = [
    path('', home, name='home'),
    path('user/signup/', signup, name='signup'),
    path('user/profile/', profile, name="profile"),
    path('user/profile/update',update_profile, name="user_update_profile"),
    path('purchase/', purhcase_credits, name='purchase' ),
    path('privacy-policy/', privacy_policy, name='privacy_policy'),
    path('tos', terms_of_service, name='tos'),
    path('refund-policy', refund_policy, name='refund_policy'),
    path('gumroad-ping-1446a', gumroad_ping, name="gumroad_ping")
]
