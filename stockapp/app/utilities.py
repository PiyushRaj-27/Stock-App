"""
Utility Functions for normal API working
"""
import requests
import json
import yfinance as yf
import pandas as pd
from pandas import DataFrame
from django.core.cache import cache
from celery import shared_task

def get_stock_1hr(stock:str) -> DataFrame:
    """
    Function to return stock data at an granuality of 1hr.
    """
    cache_key = f"stock_1hr_{stock}"  # More specific cache key
    cached_data = cache.get(cache_key)

    if cached_data:
        return pd.read_json(cached_data)  # Convert back to DataFrame

    ticker = yf.Ticker(stock)
    data = ticker.history(period="2d", interval="1h")

    if data.empty:
        return data

    cache.set(cache_key, data.to_json(), timeout=30000)  # Store as JSON, cache for 5 mins
    return data


def get_stock_15m(stock:str) -> DataFrame:
    """
    Function to return stock data at an granuality of 15minutes
    """
    cache_key = f"stock_15m_{stock}"
    cached_data = cache.get(cache_key)

    if cached_data:
        data = pd.read_json(cached_data)
        return data

    ticker = yf.Ticker(stock)
    print(ticker.__dict__)
    data = ticker.history(period="1d", interval="15m")
    if data.empty:
        return data

    # dont set cache if no data comes in
    cache.set(cache_key, data.to_json(), timeout=30000)
    return data


@shared_task
def utility_get_quaterly(stock:str) -> DataFrame:
    """
    Returns hourly stock data for a specific stock.
    """
    return get_stock_15m(stock).to_json()

@shared_task
def get_top_stock_india():
    """
    Function to return immediate stock data for top companies like nifty50
    """
    stocks = ('^NSEI', '^BSESN', 'RELIANCE.NS', 'TATAMOTORS.NS','NESTLEIND.NS','DABUR.NS','WIPRO.NS','TECHM.NS','LICI.NS','ADANIENT.NS')
    response = {}
    for stock in stocks:
        cache_key = f"stock_price_{stock}"
        cached_data = cache.get(cache_key)

        if (cached_data is not None and (not cached_data.empty)):
            response[stock] = cached_data.to_json()
            continue

        ticker = yf.Ticker(stock)
        data = ticker.history(period="1d", interval="1h")
        try:
            current_close = data['Close']
            cache.set(cache_key, current_close, timeout=30000)
            response[stock] = current_close.to_json()
        except KeyError:
            continue
    return response

@shared_task
def make_prediction(stock: str):
    """ Gives predicted value for a particular symbol.
    
        This requires some thinking i guess.
    """

    cache_key = f"app_prediction_{stock}"
    data = cache.get(cache_key)
    if data is not None:
        return data
    data = requests.get(f"http://127.0.0.1:8000/v1/stocks/{stock}")
    cache.set(cache_key, data.json(),30000)
    return data.json()