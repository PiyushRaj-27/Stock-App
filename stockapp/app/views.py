"""
Code for app endpoint
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .utilities import get_stock_1hr

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
        except:
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