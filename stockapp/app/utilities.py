"""
Utility Functions for normal API working
"""
import yfinance as yf
import pandas as pd
from pandas import DataFrame
from django.core.cache import cache
from celery import shared_task

def get_stock_1hr(stock:str) -> DataFrame:
    """
    Function to return stock data at an granuality of 1hr
    """
    cache_key = f"stock_1hr_{stock}"  # More specific cache key
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return pd.read_json(cached_data)  # Convert back to DataFrame

    ticker = yf.Ticker(stock)
    data = ticker.history(period="2d", interval="1h")

    cache.set(cache_key, data.to_json(), timeout=300)  # Store as JSON, cache for 5 mins
    return data

def get_stock_15m(stock:str) -> DataFrame:
    """
    Function to return stock data at an granuality of 1hr
    """
    cache_key = f"stock_15m_{stock}" 
    cached_data = cache.get(cache_key)
    
    if cached_data:
        data = pd.read_json(cached_data)
        return data

    ticker = yf.Ticker(stock)
    data = ticker.history(period="1d", interval="15m")
    cache.set(cache_key, data.to_json(), timeout=300) 
    return data


@shared_task
def utility_get_hourly(stock:str) -> DataFrame:
    """
    Returns hourlt stock data for a specific stock
    """
    return get_stock_15m(stock).to_json()

@shared_task
def get_top_stock_india():
    """
    Function to return immediate stock data for top companies like nifty50
    """
    stocks = ('^NSEI', '^BSESN', 'RELIANCE.NS', 'TCS.NS', 'NTPC.NS', 'TATAMOTORS.NS', 'ITC.NS')
    response = {}
    for stock in stocks:
        cache_key = f"stock_price_{stock}"
        cached_data = cache.get(cache_key)

        if cached_data:
            response[stock] = cached_data
            continue
        ticker = yf.Ticker(stock)
        data = ticker.history(period="1d", interval="1h")

        try:        
            current_close = data['Close'].iloc[-1]
            cache.set(cache_key, current_close, timeout=300)
            response[stock] = current_close
        except:
            continue
    return response
