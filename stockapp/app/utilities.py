"""
Utility Functions for normal API working
"""
import yfinance as yf
from pandas import DataFrame


def get_stock_1hr(stock:str) -> DataFrame:
    """
    Function to return stock data at an granuality of 1hr
    """
    ticker = yf.Ticker(stock)
    data =  ticker.history(period = "2d", interval = "1h")

    return data
