"""
Code for app endpoint
"""
import os
import uuid
import json
import hashlib
import logging
import requests

from celery.result import AsyncResult
from celery.exceptions import CeleryError

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, HttpResponseRedirect, HttpResponse

from users.models import Customers, PhonepayPurchase as Order, Purchase
from .utilities import (get_stock_1hr, get_top_stock_india, utility_get_quaterly, make_prediction, get_currency_stock, get_phonepay_token
                        , phonepe_order_check_celery                       
)
# logging configurations
logger = logging.getLogger(__name__)

""" Front stocks are the stocks that are displayed by default in the dashboard at the top.
    The can have been kept here, but for performance we might need to change these later.
"""
FRONT_STOCKS = ("GOOGL", "MSFT", "TSLA", "NVDA")


#TODO: Refactor this code to return celery task id to the front end rather than 
# fetching them in the request cycle.


# PHONEPAY RELATED SETTING:
MERCHANT_CALLBACK_URL = "/app/phonepay_3223/callback"
MERCHANT_REDIRECT_URL = settings.MERCHANT_REDIRECT_URL
PHONEPE_PAY_API_URL = settings.PHONEPE_API_URL + "/checkout/v2/pay"

# Create your views here.
@login_required(login_url="/accounts/login")
def dashboard(request):
    """
    Renders the main dashboard page.

    Args:
        request: The HTTP request object.

    Returns:
        The rendered dashboard template.
    """

    try:
        user = request.user
        customer = Customers.objects.get(user=user)
    except (ObjectDoesNotExist):
        return redirect("/user/profile")
    labels_list = []
    data_list = []
    names = []
    real = []
    currency = []
    realname = {"GOOGL": "Google", "MSFT": "Microsoft", "TSLA": "Tesla", "NVDA": "Nvidia"}
    for stock in FRONT_STOCKS:
        try:
            temp = get_stock_1hr(stock, 5)
            labels = temp.index.strftime('%H').tolist()
            data = temp["Close"].tolist()
            labels_list.append(labels[:])
            data_list.append(data[:])
            names.append(stock)
            real.append(realname[stock])
            currency.append(get_currency_stock(stock))
        except Exception:
            continue
    data = list(map(list, list(zip(labels_list, data_list, names, real, currency))))
    return render(request, "app/dashboard.html",{"data":data})



@login_required(login_url="/accounts/login")
def search(request):
    """
    Handles stock search requests.

    If a POST request is received, it extracts the stock symbol from the request,
    prints it to the console, and renders the stock dashboard template with the
    stock symbol.  Otherwise, it redirects to the main dashboard.

    Args:
        request: The HTTP request object.

    Returns:
        The rendered stock dashboard template (if POST request with stock symbol),
        or a redirect to the main dashboard.
    """
    if request.method == "POST":

        stock_name: str = request.POST.get("stock", "").strip().upper()

        if stock_name:
            return render(request, "app/stockdashboard.html", {'stock_name': stock_name})

        logger.error("Search POST request missing stock value")

    return redirect("/app/dashboard")


@login_required(login_url="/accounts/login")
def stock_dashboard(request, stockname: str):
    """
    Handles stock specific dashboard.

    It extracts stock symbol from the request url and returns the stock specific dashboard.

    Returns:
        The redered stock specific dashboard template.
    """
    stock_name: str = stockname.strip().upper()

    return render(request, "app/stockdashboard.html", {'stock_name':stock_name})



@login_required(login_url="/accounts/login")
def trigger_top_india_stock_task(request):
    """
    API end point that handles fetching top indian stocks data.
    It creates a celery task and returns the task id as a response.

    Returns:
        JsonResponse: Contains the task_id for polling.

        In case of error return success as False
    """
    _ = request

    try:
        top_india_data_task = get_top_stock_india.delay()
        return JsonResponse({"task_id": top_india_data_task.id, "success": True})

    except CeleryError as e:
        logger.error("Celery task initation failed: %s", e)
        return JsonResponse({"task_id": "-1", "success": False}, status = 500)

    except Exception as e:
        logger.error("Exception occured while polling task: %s", e)
        return JsonResponse({'status': "FAILURE", 'result': None}, status = 500)


@login_required(login_url="/accounts/login")
def get_task_result(request):
    """
    End point to poll for result of execution of Celery background task.

    Query Parameters:
        task_id (str): The ID of the Celery task to check.

    Returns:
        JsonResponse: Contains the task status ('PENDING', 'SUCCESS', 'FAILURE', etc.)
                      and the result (if successful) or error details (if failed).
    """
    _ = request
    task_id = request.GET.get('task_id', "")

    if not task_id:
        logger.error("Invalid task id polled from Celery")
        return JsonResponse({'status': "FAILURE", 'result': None})

    try:
        result = AsyncResult(task_id)

        if result.failed():
            logger.error("Celery task failed for task id: %s, traceback: %s",task_id, result.info)

        return JsonResponse({'status': result.status, 'result': result.result})

    except CeleryError as e:
        logger.error("Celery task polling failed due to CeleryError: %s", e)
        return JsonResponse({'status': "FAILURE", 'result': None}, status = 500)

    except Exception as e:
        logger.error("Exception while initating Celery task: with message: %s", e)
        return JsonResponse({'status': "FAILURE", 'result': None})

@login_required(login_url="/accounts/login")
def trigger_get_hourly_task(request, stockname):
    """
    End point to return task id for quaterly utility execution
    """
    _ = request
    stock_name: str = stockname.strip().upper()

    if not stock_name:
        logger.error("Invalid stock name for trigger_get_hourly_task, stock_name: %s", stock_name)
        return JsonResponse({"task_id": "-1", "success": False})

    try:
        hourly_task = utility_get_quaterly.delay(stock_name)
        return JsonResponse({"task_id": hourly_task.id, "success": True})

    except CeleryError as e:
        logger.error("Celery task initation failed: %s", e)
        return JsonResponse({"task_id": "-1", "success": False})

    except Exception as e:
        logger.error("Exception while initating Celery task: trigger_get_hour_task with message: %s", e)
        return JsonResponse({"task_id": "-1", "success": False})


@login_required(login_url="/accounts/login")
def trigger_get_prediction_task(request, stockname):
    """
    End point to fetch prediction for stockname
    """

    _ = request
    stock_name: str = stockname.strip().upper()

    if not stock_name:
        logger.error("Invalid stock name for get_prediction, stock_name: %s", stock_name)
        return JsonResponse({"task_id": "-1", "success": False})

    try:
        prediction_task = make_prediction.delay(stockname, request.user.email)
        return JsonResponse({'task_id': prediction_task.id, "success": True})

    except CeleryError as e:
        logger.error("Celery task initation failed: %s", e)
        return JsonResponse({"task_id": "-1", "success": False})

    except Exception as e:
        logger.error("Exception while initating Celery task: get_prediction with message: %s", e)
        return JsonResponse({"task_id": "-1", "success": False})



# Payment related stuff here!
@login_required(login_url="/accounts/login")
def initiate_phonepay_payment(request):
    """
    Handle the user payment initiation.
    """
    if request.method == "POST":
    
        item_id = request.POST.get("itemId", "")
        if item_id == '1':
            amount = 99 * 100
        elif item_id == '2':
            amount = 149 * 100
        elif item_id == '3':
            amount = 199 * 100

        else:
            return JsonResponse({"message": "Payment Initiation Failed. Invalid item_id param"})


        try:
            auth_token = get_phonepay_token()

        except Exception as e:
            logger.error("Payment initiation failed: Auth token fetch failed: %s", e)
            return JsonResponse({"message": "Payment Initiation Failed. Our Dev team is working on the error. Please try again later."})


        # generate the redirect url and the purchase object
        merchant_order_id = f"MERCH_DBLACS_ORD_{uuid.uuid4().hex[:10].upper()}"
        order = Order.objects.create(
            merchant_order_id=merchant_order_id,
            user_id = request.user,
            amount=amount,
            status='PENDING'
        )
        try:

            with transaction.atomic():


                # prepare body and header to obtaining phonepay payment redirect
                callback_url = request.build_absolute_uri(MERCHANT_REDIRECT_URL)
                callback_url += f"?merchantOrderId={merchant_order_id}"
                payment_payload = {
                    "merchantOrderId": order.merchant_order_id,
                    "amount": order.amount,
                    "expireAfter": 1200, # 20 minutes
                    "metaInfo": {
                        "merchantOrderId": order.merchant_order_id,
                    },
                    "paymentFlow": {
                        "type": "PG_CHECKOUT",
                        "merchantUrls": {
                            # This is where the user is redirected *after* payment completion
                            "redirectUrl": callback_url 
                        }
                    }
                }

                payment_headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'O-Bearer {auth_token}'
                }


                payment_response = requests.post(
                        PHONEPE_PAY_API_URL,
                        json=payment_payload,
                        headers=payment_headers,
                        timeout=100
                    )
                payment_response.raise_for_status()
                payment_data = payment_response.json()

                # The all-important URL to send the user to
                redirect_url = payment_data.get('redirectUrl')

                if not redirect_url:
                    order.status = 'FAILED'
                    order.save()
                    return JsonResponse({"message": "Payment Initiation Failed. Our Dev team is working on the error. Please try again later."})

                # Save the PhonePe Order ID for reference
                order.phonepe_order_id = payment_data.get('orderId')
                order.save()

            # Redirect the user to the PhonePe payment page
            # This is the "Redirect Mode" from the documentation.
            # We don't need the checkout.js for this simple mode.
            # return HttpResponseRedirect(redirect_url)
            return render(request, "app/payment.html", context= {"redirect_url": redirect_url, "merchantOrderId":merchant_order_id})
        except Exception as e:
            logger.error("Payment initiation failed %s",e)
            order.status = 'FAILED'
            order.save()
            return JsonResponse({"message": "Payment Initiation Failed. Our Dev team is working on the error. Please try again later."})

    return redirect("/purchase")


@csrf_exempt # Important! PhonePe won't have a CSRF token
def phonepe_payment_callback(request):
    """
    Handles the phonepe webhook
    """
    if request.method != 'POST':
        logger.warning("Webhook received with invalid method: %s", request.method)
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    # 1. --- SECURITY: Verify the incoming request (Your existing code is good) ---
    try:
        webhook_user = os.environ.get("PHONEPE_WEBHOOK_USERNAME")
        webhook_pass = os.environ.get("PHONEPE_WEBHOOK_PASSWORD")

        if not webhook_user or not webhook_pass:
            logger.error("Webhook credentials are not set in environment.")
            return JsonResponse({'status': 'error', 'message': 'Internal configuration error.'}, status=500)

        expected_auth_str = f"{webhook_user}:{webhook_pass}"
        expected_hash = hashlib.sha256(expected_auth_str.encode('utf-8')).hexdigest()
        received_hash = request.headers.get('Authorization')

        if received_hash != expected_hash:
            logger.warning("Webhook received with invalid Authorization header.")
            return JsonResponse({'status': 'error', 'message': 'Authorization failed.'}, status=401)
    except Exception as e:
        logger.error("Error during webhook authentication: %s", e)
        return JsonResponse({'status': 'error', 'message': 'Internal server error.'}, status=500)

    # 2. --- Process the Payload ---
    try:
        data = json.loads(request.body)
        event = data.get('event')
        payload = data.get('payload', {})

        if event in ('checkout.order.failed','checkout.order.completed'):
            merchant_order_id = payload.get('merchantOrderId')
        else:
            merchant_order_id = payload.get('originalMerchantOrderId')

        if not merchant_order_id:
            logger.warning("Webhook received without a merchantOrderId.")
            return JsonResponse({'status': 'error', 'message': 'Missing merchantOrderId.'}, status=400)

        # CRITICAL FIX: Wrap the entire database operation in a transaction
        with transaction.atomic():
            # Use select_for_update to lock the row and prevent race conditions
            order = Order.objects.select_for_update().get(merchant_order_id=merchant_order_id)

            # CRITICAL FIX: Idempotency Check. If already processed, just acknowledge.
            if order.status == 'SUCCESS': # dont check for FAILED though
                logger.info("Webhook for already completed order %s received. Ignoring.", merchant_order_id)
                return JsonResponse({'status': 'ok', 'message': 'Already processed.'})

            # Store the raw response for auditing
            order.raw_response_data = data
            order.webhook_event = event

            # Handle different event types
            if event == 'checkout.order.completed' and payload.get("state") == "COMPLETED":
                order.status = 'SUCCESS'
                payment_details = payload.get('paymentDetails', [{}])[0]
                order.phonepe_transaction_id = payment_details.get('transactionId')

                # --- Your Business Logic Starts Here ---
                amount_paid = order.amount # Trust the amount from our DB

                try:
                    # Get the Customer model associated with the User who made the order
                    customer = Customers.objects.get(user=order.user_id)
                except ObjectDoesNotExist:
                    logger.error("Customer not found for user %s on order %s", order.user_id.username, merchant_order_id)
                    # The transaction will be rolled back, so the order status won't be saved as SUCCESS
                    # This is correct behavior, as we can't award credits.
                    raise # Raising an exception aborts the transaction
                if amount_paid == 99 * 100:
                    customer.credit += 2
                elif amount_paid == 149 * 100:
                    customer.credit += 7
                elif amount_paid == 199 * 100:
                    customer.credit += 11
                else:
                    logger.error("Invalid amount value (%s) for order %s. No credits awarded.", amount_paid, merchant_order_id)
                    # Decide if you still want to mark the order as SUCCESS or not.
                    # For now, we will, but we won't award credits.

                # CRITICAL FIX: Save the updated customer object
                customer.save()
                order.save() # Save the order after all changes are done
                logger.info("Order %s completed successfully. Credits awarded to %s.", merchant_order_id, customer.user.username)

            elif event == 'checkout.order.failed':
                order.status = 'FAILED'

                # CRITICAL FIX: Safely get transactionId
                payment_details_list = payload.get('paymentDetails', [])
                if payment_details_list:
                    order.phonepe_transaction_id = payment_details_list[0].get('transactionId')

                order.save()
                logger.warning("Order %s failed.", merchant_order_id)


            elif event == 'pg.refund.accepted':
                # This event confirms PhonePe has accepted the refund request.
                order.status = 'REFUND_CONFIRMED'
                order.phonepe_refund_id = payload.get('refundId') # Store the PhonePe refund ID
                order.save()
                logger.info("Refund for order %s was accepted by PhonePe.")

            elif event == 'pg.refund.completed' and payload.get("state") == "COMPLETED":
                # This is the final success state for a refund.
                order.status = 'REFUNDED'
                order.save()
                logger.info("Refund for order %s completed successfully.", merchant_order_id)
                # --- Business Logic (e.g., revoking access/credits) can go here ---

            elif event == 'pg.refund.failed' and payload.get("state") == "FAILED":
                # This is the final failure state for a refund.
                order.status = 'REFUND_FAILED'
                order.save()
                error_code = payload.get('errorCode', 'N/A')
                logger.error("Refund for order %s failed with error code: %s.", merchant_order_id, error_code)
            else:
                logger.info("Received unhandled webhook event: %s for order %s", event, merchant_order_id)

        # 3. --- Acknowledge Receipt ---
        return JsonResponse({'status': 'ok', 'message': 'Webhook processed successfully.'})

    except Order.DoesNotExist:
        logger.error("Webhook received for non-existent order: %s", merchant_order_id)
        return JsonResponse({'status': 'error', 'message': 'Order not found.'}, status=404)
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON from webhook body.")
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)
    except Exception as e:
        logger.error("Unexpected error processing webhook for order %s: %s", merchant_order_id, e)
        # The transaction.atomic() block will automatically roll back on any exception
        return JsonResponse({'status': 'error', 'message': 'Internal server error.'}, status=500)


@login_required(login_url="/accounts/login")
def phonepe_redirect_callback(request):
    """
    Merchant redirect url
    """

    # get the merchantorderid
    merchantOrderId = request.GET.get("merchantOrderId")
    if not merchantOrderId:
        return JsonResponse({"message": "Due to internal server error, We cannot fetch the order status, please go to profile section to see if purchase was successful", "task_id": "-1", "success": False})

    # get the phonepe purchase
    try:
        order = Order.objects.get(merchant_order_id=merchantOrderId)

        if order and order.user_id == request.user:
            # okay, call the status check api and return the response :)
            # if the order.status is not pending return it! #TODO

            # get the celery token for the order check api and send it to frontend, where check would happen until a terminal state is reached!
            order_check_task_id = phonepe_order_check_celery.delay(merchantOrderId)
            return render(request, "app/payment.html", {"task_id" : order_check_task_id})
        else:
            return JsonResponse({"message": "Unauthorized status check"})

    except Order.DoesNotExist:
        return JsonResponse({"message": "Order Not Found", "task_id": "-1", "success": False})

    except CeleryError as e:
        logger.error("Celery task initation failed: %s", e)
        return JsonResponse({"task_id": "-1", "success": False})

    except Exception as e:
        logger.error("Exception while initating Celery task: get_prediction with message: %s", e)
        return JsonResponse({"task_id": "-1", "success": False})


@login_required
def user_purchase_history(request):
    """
    Collects and displays a unified purchase history for the logged-in user
    from both Gumroad (Purchase) and PhonePe (PhonepayPurchase) sources.
    """

    # This list will hold our standardized purchase data
    all_purchases = []

    gumroad_purchases = Purchase.objects.filter(customer__user=request.user)

    for p in gumroad_purchases:
        # Prepare the data in the required tuple format
        # Note: We convert price from cents to a standard currency unit
        processed_purchase = (
            p.sale_timestamp,             # date_and_time
            p.price_cents / 100.0,        # amount
            "GUMROAD",                    # payment_mode
            p.sale_id,                    # unique_purchase_no
            "SUCCESS"                     # status (always SUCCESS as per requirement)
        )
        all_purchases.append(processed_purchase)

    # --- Step 2: Fetch and process PhonePe purchases ---
    # Here, the user is linked directly
    phonepe_purchases = Order.objects.filter(user_id=request.user)
    
    for p in phonepe_purchases:
        # Prepare the data in the same tuple format
        # Note: We convert amount from paisa to rupees
        processed_purchase = (
            p.created_at,                 # date_and_time
            p.amount / 100.0,             # amount
            "PHONEPE",                    # payment_mode
            p.merchant_order_id,          # unique_purchase_no
            p.status        # status (e.g., 'Success', 'Pending')
        )
        all_purchases.append(processed_purchase)

    # --- Step 3: Sort the combined list by date, most recent first ---
    # The first element (index 0) of our tuple is the datetime object
    all_purchases.sort(key=lambda purchase: purchase[0], reverse=True)

    # --- Step 4: Pass the final list to the template ---
    context = {
        'purchase_history': all_purchases
    }
    # return JsonResponse({"vals": all_purchases})
    return render(request, 'app/payment_history.html', context)