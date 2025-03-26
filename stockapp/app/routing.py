from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/stock/(?P<stock_name>[\w\.]+)/$", consumers.StockConsumer.as_asgi()),
]