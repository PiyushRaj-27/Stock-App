"""
Module for defining User models
"""

from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Customers(models.Model):
    """
    Base class for all the customers.
    Information such as Username, Userpassword, Email and Password are stored
    on the User model. Only other relevant information are stored here.
    """
    # user = models.ForeignKey(User, on_delete=models.CASCADE, blank= True, primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True)
    phone = models.CharField(max_length=10)
    credit = models.IntegerField(default=0)
    countryCode = models.CharField( max_length=3, default="")
    gender = models.CharField(max_length=10, default="Male")
    @property
    def credit_points(self):
        """
        Returns the credit the user has remaining
        """
        return self.credit

    def save(self, **kwargs):
        """
        Prevent saving if phone number is less than 10
        """
        # if len(self.phone) != 10:
        #     return 
        return super().save(**kwargs)
    