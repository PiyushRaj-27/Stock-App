from django.contrib import admin
from django.contrib.admin import site
from .models import Customers

site.register(Customers)

# Register your models here.
