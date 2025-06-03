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
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key = True)
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

    def save(self,*args, **kwargs):
        """
        Prevent saving if phone number is less than 10
        """
        # if len(self.phone) != 10:
        #     return 
        return super().save(**kwargs)

class Purchase(models.Model):
    """
    This Model represents a purchase from gumroad.
    Stores infromation related to a purchase that was made.
    """
    customer = models.ForeignKey(Customers, on_delete=models.DO_NOTHING, related_name='purchases', blank=True)
    sale_id = models.CharField(max_length=100, unique=True)
    sale_timestamp = models.DateTimeField()
    order_number = models.CharField(max_length=100)
    product_id = models.CharField(max_length=100)
    product_permalink = models.CharField(max_length=255)
    short_product_id = models.CharField(max_length=100)
    product_name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    price_cents = models.IntegerField()
    quantity = models.IntegerField(default=1)
    ip_country = models.CharField(max_length=100, null=True, blank=True)
    affiliate_email = models.EmailField(null=True, blank=True)
    refunded = models.BooleanField(default=False)
    custom_email_id = models.EmailField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.user.email} - {self.product_name}"
