"""
Admin configurations
"""
import uuid
import requests
import logging
from django.contrib import admin, messages
from django.http import HttpResponse
from django.contrib.admin import site
from django.contrib.admin import ModelAdmin
from django.conf import settings
from .models import Customers, PhonepayPurchase, Purchase
from app.utilities import phonepe_check_order_status, get_phonepay_token

logger = logging.getLogger(__name__)


site.register(Customers)
site.register(Purchase)
site.register(PhonepayPurchase)
# Register your models here.


@admin.action(description="Initiate PhonePe Refund")
def initiate_refund(modeladmin, request, queryset):
    """
    Admin action to initiate Refunds for the selected purchases in queryset
    """
    successful_initiations = 0

    # 1. Filter for only refundable purchases to avoid unnecessary API calls
    refundable_purchases = queryset.filter(status='SUCCESS')

    # Notify admin about non-refundable items that were selected
    non_refundable_count = queryset.exclude(pk__in=refundable_purchases.values_list('pk', flat=True)).count()
    if non_refundable_count > 0:
        modeladmin.message_user(
            request,
            f"{non_refundable_count} selected purchase(s) were not in a refundable state ('SUCCESS') and were skipped."
        )

    # 2. Loop through only the valid, refundable purchases
    for purchase in refundable_purchases:
        try:
            # 3. Prepare the API Request
            # Generate a unique merchant refund ID as required by PhonePe
            merchant_refund_id = f"REF_{purchase.merchant_order_id}_{uuid.uuid4().hex[:8]}"

            # Get the auth token
            auth_token = get_phonepay_token()

            # Prepare headers and payload
            refund_headers = {
                "Content-Type": "application/json",
                "Authorization": f"O-Bearer {auth_token}"
            }
            refund_payload = {
                "merchantRefundId": merchant_refund_id,
                "originalMerchantOrderId": purchase.merchant_order_id,
                "amount": purchase.amount  # Assumes amount is already in paisa
            }
            refund_url = settings.PHONEPE_API_URL + "/payments/v2/refund"

            # 4. Make the API Call
            response = requests.post(
                url=refund_url,
                headers=refund_headers,
                json=refund_payload,
                timeout=100
            )
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

            response_data = response.json()

            # 5. Process the API Response and Update Database
            if response_data.get("state") == "PENDING":
                purchase.status = 'REFUND_INITIATED'
                purchase.merchant_refund_id = merchant_refund_id
                purchase.phonepe_refund_id = response_data.get("refundId")
                purchase.save()

                modeladmin.message_user(
                    request,
                    f"Refund initiated successfully for Order ID: {purchase.merchant_order_id}"
                )
                successful_initiations += 1
            else:
                # This case is unlikely if raise_for_status() is used, but good for safety
                error_message = response_data.get('message', 'Unknown error from PhonePe.')
                modeladmin.message_user(
                    request,
                    f"Failed to initiate refund for Order ID {purchase.merchant_order_id}: {error_message}"
                )

        except requests.exceptions.HTTPError as e:
            # Handle specific HTTP errors (like 400, 401, 500)
            error_details = e.response.json().get('message', e.response.text)
            # logger.error(f"HTTP Error initiating refund for {purchase.merchant_order_id}: {error_details}")
            modeladmin.message_user(
                request,
                f"API Error for Order ID {purchase.merchant_order_id}: {error_details}"
            )
        except Exception as e:
            # Handle other exceptions like network issues or token fetch failure
            # logger.error(f"An unexpected error occurred while initiating refund for {purchase.merchant_order_id}: {e}")
            modeladmin.message_user(
                request,
                f"An unexpected error occurred for Order ID {purchase.merchant_order_id}. Check logs: {e}"
            )

    if successful_initiations > 0:
        modeladmin.message_user(
            request,
            f"Process complete. Successfully initiated refunds for {successful_initiations} purchase(s)."
        )


@admin.action(description="Check Refund Status")
def check_refund_status(modeladmin, request, queryset):
    """
    Admin action to check refund status via payment status api
    """
    successful_updates = 0
    # 1. Filter for purchases that have a refund initiated
    eligible_purchases = queryset.filter(status='REFUND_INITIATED').exclude(merchant_refund_id__isnull=True)

    # Notify admin about non-eligible items that were selected
    skipped_count = queryset.exclude(pk__in=eligible_purchases.values_list('pk', flat=True)).count()
    if skipped_count > 0:
        modeladmin.message_user(
            request,
            f"{skipped_count} selected purchase(s) were not in a 'REFUND_INITIATED' state and were skipped.",
            messages.WARNING
        )

    # 2. Loop through only the eligible purchases
    for purchase in eligible_purchases:
        try:
            # 3. Prepare the API Request
            merchant_refund_id = purchase.merchant_refund_id
            auth_token = get_phonepay_token()

            status_headers = {
                "Content-Type": "application/json",
                "Authorization": f"O-Bearer {auth_token}"
            }
            status_url = f"{settings.PHONEPE_API_URL}/payments/v2/refund/{merchant_refund_id}/status"

            # 4. Make the API Call
            response = requests.get(
                url=status_url,
                headers=status_headers,
                timeout=100
            )
            response.raise_for_status()
            response_data = response.json()

            # 5. Process the API Response and Update Database
            api_state = response_data.get("state")
            original_status = purchase.status

            new_status = None
            if api_state == 'COMPLETED':
                new_status = 'REFUNDED'
            elif api_state == 'FAILED':
                new_status = 'REFUND_FAILED'
            elif api_state == 'CONFIRMED':
                new_status = 'REFUND_CONFIRMED'

            if new_status and new_status != original_status:
                purchase.status = new_status
                purchase.save()
                successful_updates += 1
                modeladmin.message_user(
                    request,
                    f"Status for Order {purchase.merchant_order_id} updated to {new_status}.",
                    messages.SUCCESS
                )
            else:
                modeladmin.message_user(
                    request,
                    f"Refund status for Order {purchase.merchant_order_id} is still '{api_state}'. No change made.",
                    messages.INFO
                )

        except requests.exceptions.HTTPError as e:
            error_details = e.response.json().get('message', e.response.text)
            logger.error(f"HTTP Error checking refund status for {purchase.merchant_order_id}: {error_details}")
            modeladmin.message_user(
                request,
                f"API Error for Order ID {purchase.merchant_order_id}: {error_details}",
                messages.ERROR
            )
        except Exception as e:
            logger.error(f"An unexpected error occurred while checking refund for {purchase.merchant_order_id}: {e}")
            modeladmin.message_user(
                request,
                f"An unexpected error occurred for Order ID {purchase.merchant_order_id}. Check logs.",
                messages.ERROR
            )

    if successful_updates > 0:
        modeladmin.message_user(
            request,
            f"Process complete. Updated {successful_updates} refund status(es).",
            messages.INFO
        )





@admin.action(description="Check Payment Status")
def check_payment_status(modeladmin, request, queryset):
    """
    Admin action to check payment status via payment status api
    """
    for q in queryset:
        # call the check order status function
        orderId = q.merchant_order_id
        status = phonepe_check_order_status(orderId)
        admin.ModelAdmin.message_user(modeladmin, request=request, message=f"status for orderId: {orderId} is : {status}")


class PhonepayPurchaseAdmin(admin.ModelAdmin):
    """
    Class for actions
    """
    list_display = ('merchant_order_id', 'user_id', 'status', 'amount', 'phonepe_transaction_id', 'updated_at')
    list_filter = ('status',)
    search_fields = ('merchant_order_id', 'phonepe_transaction_id', 'user_id__username')
    readonly_fields = ('created_at', 'updated_at', 'merchant_refund_id', 'phonepe_refund_id')
    actions = [initiate_refund,check_payment_status, check_refund_status]


if admin.site.is_registered(PhonepayPurchase):
    admin.site.unregister(PhonepayPurchase)
admin.site.register(PhonepayPurchase, PhonepayPurchaseAdmin)
