"""
Code for app endpoint
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from celery.result import AsyncResult

from .utilities import get_stock_1hr, get_top_stock_india, utility_get_quaterly, make_prediction

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
    for stock in ("GOOGL", "MSFT", "TSLA", "NVDA"):
        try:
            temp = get_stock_1hr(stock)
            labels = temp.index.strftime('%H').tolist()
            data = temp["Close"].tolist()
            labels_list.append(labels[-7:])
            data_list.append(data[-7:])
            names.append(stock)
        except Exception:
            continue
    data = list(map(list, list(zip(labels_list, data_list, names))))
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
        return render(request, "app/stockdashboard.html", {'stock_name': request.POST["stock"]})

    return redirect("/app/dashboard")


@login_required(login_url="/accounts/login")
def stock_dashboard(request, stockname: str):
    """
    Handles stock specific dashboard.

    It extracts stock symbol from the request url and returns the stock specific dashboard.

    Returns:
        The redered stock specific dashboard template.
    """

    return render(request, "app/stockdashboard.html", {'stock_name':stockname})

@login_required(login_url="/accounts/login")
def top_india_stock(request):
    """
    API end point that handles fetching top indian stocks data.

    It creates a celery task and returns the task id as a response.

    Returns:
        JSON reponse for task id.
    """

    top_india_data_task = get_top_stock_india.delay()
    return JsonResponse({"task_id": top_india_data_task.id})

@login_required(login_url="/accounts/login")
def get_result(request):
    """
    End point to poll for result of execution of celery background task.
    """
    task_id = request.GET.get('task_id')
    result = AsyncResult(task_id)

    return JsonResponse({'status': result.status, 'result': result.result})

@login_required(login_url="/accounts/login")
def get_hourly(request, stockname):
    """
    End point to return task id for quaterly utility execution
    """
    hourly_task = utility_get_quaterly.delay(stockname)
    return JsonResponse({"task_id": hourly_task.id})

@login_required(login_url="/accounts/login")
def get_prediction(requst, stockname):
    """
    End point to fetch prediction for stockname
    """
    prediction_task = make_prediction.delay(stockname)
    return JsonResponse({'task_id': prediction_task.id})
