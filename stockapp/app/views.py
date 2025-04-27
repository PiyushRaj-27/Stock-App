"""
Code for app endpoint
"""
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from celery.result import AsyncResult
from celery.exceptions import CeleryError
from .utilities import get_stock_1hr, get_top_stock_india, utility_get_quaterly, make_prediction

# logging configurations
logger = logging.getLogger(__name__)

""" Front stocks are the stocks that are displayed by default in the dashboard at the top.
    The can have been kept here, but for performance we might need to change these later.
"""
FRONT_STOCKS = ("GOOGL", "MSFT", "TSLA", "NVDA")


# TODO: Refactor this code to return celery task id to the front end rather than 
# fetching them in the request cycle.


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
    labels_list = []
    data_list = []
    names = []
    real = []
    realname = {"GOOGL": "Google", "MSFT": "Microsoft", "TSLA": "Tesla", "NVDA": "Nvidia"}
    for stock in ("GOOGL", "MSFT", "TSLA", "NVDA"):
        try:
            temp = get_stock_1hr(stock, 5)
            labels = temp.index.strftime('%H').tolist()
            data = temp["Close"].tolist()
            labels_list.append(labels[:])
            data_list.append(data[:])
            names.append(stock)
            real.append(realname[stock])

        except Exception:
            continue
    data = list(map(list, list(zip(labels_list, data_list, names, real))))
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
        return JsonResponse({'status': "FAILURE", 'result': None})


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
        return JsonResponse({'status': "FAILURE", 'result': None})

    except Exception as e:
        logger.error("Exception while initating Celery task: trigger_top_india_stock_task with message: %s", e)
        return JsonResponse({"task_id": "-1", "success": False})

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
        prediction_task = make_prediction.delay(stockname)
        return JsonResponse({'task_id': prediction_task.id, "success": True})

    except CeleryError as e:
        logger.error("Celery task initation failed: %s", e)
        return JsonResponse({"task_id": "-1", "success": False})

    except Exception as e:
        logger.error("Exception while initating Celery task: get_prediction with message: %s", e)
        return JsonResponse({"task_id": "-1", "success": False})

