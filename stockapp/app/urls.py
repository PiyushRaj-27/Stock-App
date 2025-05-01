"""
URL configuration for stockapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from .views import (dashboard, search,
                     stock_dashboard,
                    get_task_result, trigger_top_india_stock_task, trigger_get_hourly_task, trigger_get_prediction_task)
urlpatterns = [
    path('dashboard/', dashboard, name="dashboard"),
    path('search/', search, name="search"),
    path('top_stock/', trigger_top_india_stock_task, name="top_stock"),
    path('infer/', get_task_result, name = "infer"),
    path('stock/<str:stockname>', stock_dashboard, name="stock"),
    path("stock/hourly/<str:stockname>", trigger_get_hourly_task, name="hourly"),
    path('stock/prediction/<str:stockname>', trigger_get_prediction_task, name="prediction")
]
