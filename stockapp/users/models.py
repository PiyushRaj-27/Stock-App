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


class PhonepayPurchase(models.Model):
    """
    PhonePe purchase records for the website.
    """


    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'), # This is a refundable state
        ('FAILED', 'Failed'),
        ('REFUND_INITIATED', 'Refund Initiated'), # New status
        ('REFUNDED', 'Refunded'),               # New status (from webhook)
        ('REFUND_CONFIRMED', 'Refund confirmed'),
        ('REFUND_FAILED', 'Refund Failed'),     # New status (from webhook)
    )

    # Use merchantOrderId as the primary key if you want it to be unique,
    # or just ensure it's unique with unique=True.
    merchant_order_id = models.CharField(max_length=63, unique=True, primary_key=True)

    user_id = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='phonepaypayments')

    # Store amount in the smallest currency unit (paisa)
    amount = models.PositiveIntegerField() 

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    # Store the PhonePe generated orderId for reference
    phonepe_order_id = models.CharField(max_length=100, blank=True, null=True)

    # Store the final transaction ID from the webhook
    phonepe_transaction_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)

    # Store the last webhook event type received (e.g., 'checkout.order.completed')
    webhook_event = models.CharField(max_length=50, blank=True, null=True)

    # Store the raw webhook response for debugging purposes
    raw_response_data = models.JSONField(null=True, blank=True)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # The unique ID we generate for our refund request
    merchant_refund_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    # The transaction ID PhonePe returns for the refund
    phonepe_refund_id = models.CharField(max_length=100, unique=True, null=True, blank=True)

    # You would also link this to a User model
    # user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Order {self.merchant_order_id} - {self.status}"

    @property
    def is_refundable(self):
        """
        To check if the order is refundable.
        """
        # A property to easily check if the action should be available
        return self.status == 'SUCCESS'