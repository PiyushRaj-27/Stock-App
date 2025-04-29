"""
Utility Functions for normal API working
"""
import json
import logging
import requests
import yfinance as yf
import pandas as pd
from pandas import DataFrame
from django.core.cache import cache
from yfinance.exceptions import YFException
from celery import shared_task

logger = logging.getLogger(__name__)

HISTORY_TIMEOUT = 300000
INFO_TIMEOUT = 300000


def get_stock_data(stock: str, period:str = "1d", interval:str = "15m",
                historyOnly: bool = False, informationOnly: bool = False) -> dict:
    """
    Returns the stock data for a given stock symbol for specified period and interval.
    Assumes the stock parameter is already cleaned
    Parameters:
        Stock: Stock symbols
        Period: Period for historical data
        interval: Interval of time
    Returns:
        Dictionary: {history: Dataframe | None , info: Dictionary | None}
    """

    cache_key_history = f"stock_{period}_{interval}_{stock}_history"
    cache_key_info = f"stock_{stock}_information"
    history = None
    info = None

    try:
        history_json = cache.get(cache_key_history, "")
        history = pd.read_json(history_json)
        info_json = cache.get(cache_key_info, "")
        info = json.loads(info_json)

    except ConnectionError as e:
        logger.error("Connection to redis cache failed. Fallback to live: %s", e)

    except TimeoutError as e:
        logger.error("Redis took too long to response: %s", e)

    except Exception as e:
        logger.error("Cache get failed with exception: %s .Fallback to live", e)

    if (history is None or history.empty) and not informationOnly:
        logger.warning("Fetching live data for stock %s", stock)

        try:
            ticker = yf.Ticker(stock)
            history = ticker.history(period=period, interval=interval)

            try:
                cache.set(cache_key_history, history.to_json(), timeout=HISTORY_TIMEOUT)

            except ConnectionError as e:
                logger.error("Connection to redis cache failed. Data cannot be cached: %s", e)

            except TimeoutError as e:
                logger.error("Redis took too long to response: %s", e)

            except Exception as e:
                logger.error("cache set failed: %s .Data cannot be cached", e)

        except YFException as e:
            logger.log("Failed to fetch history from Yfinance %s", e)
            history = None


    if (info is None or not info) and not historyOnly:
        logger.warning("Fetching live info for stock %s", stock)

        try:
            ticker = yf.Ticker(stock)
            info = ticker.info

            try:
                cache.set(cache_key_info, json.dumps(info), timeout=HISTORY_TIMEOUT)

            except ConnectionError as e:
                logger.error("Connection to redis cache failed. Data cannot be cached: %s", e)

            except TimeoutError as e:
                logger.error("Redis took too long to response: %s", e)

            except Exception as e:
                logger.error("cache set failed: %s .Data cannot be cached", e)

        except YFException as e:
            logger.log("Failed to fetch history from Yfinance %s", e)
            info = None


    if historyOnly:
        return {"history": history, "info": None}

    elif informationOnly:
        return {"history": None, "info": info}

    else:
        return {"history": history, "info": info}



def get_stock_1hr(stock:str, n_days:str = 1) -> DataFrame | None:
    """
    Utility function to return stock historical data for the last 2 days
    at a granularity of 1 hour for a given stock symbol.

    Leverages the get_stock_data function for fetching and caching.

    Parameters:
        stock: The stock symbol (e.g., "AAPL", "MSFT").

    Returns:
        pandas.DataFrame | None: A DataFrame containing the 1-hour historical data
                                  for the specified period ("2d"), or None if data
                                  could not be fetched or an error occurred in
                                  the underlying get_stock_data call. Can return
                                  an empty DataFrame if yfinance provides one.
    """

    data = get_stock_data(stock, f"{n_days}d", "1h", historyOnly=True)
    history_df = data.get("history")

    if history_df is None or history_df.empty:
        logger.warning("API returned Empty data for symbol %s", stock)

    return history_df


def get_stock_15m(stock:str) -> DataFrame | None:
    """
    Utility function to return stock historical data for the last 1 day
    at a granularity of 15 minutes for a given stock symbol.

    Leverages the get_stock_data function for fetching and caching.

    Parameters:
        stock: The stock symbol (e.g., "AAPL", "MSFT").

    Returns:
        pandas.DataFrame | None: A DataFrame containing the 15-minute historical data
                                  for the specified period ("1d"), or None if data
                                  could not be fetched or an error occurred in
                                  the underlying get_stock_data call. Can return
                                  an empty DataFrame if yfinance provides one.
    """
    logger.info("Requesting 15m data (period=1d) for %s via get_stock_data", stock)

    stock_data_dict = get_stock_data(stock=stock, period="1d",interval="15m",historyOnly=True)

    history_df = stock_data_dict.get("history")

    if history_df is None:
        logger.warning("get_stock_data returned None for history for %s", stock)

    elif history_df.empty:
        logger.info("get_stock_data returned an empty DataFrame for history for %s", stock)

    return history_df


@shared_task
def utility_get_quaterly(stock:str) -> DataFrame:
    """
    Utility function to return stock historical data for the last 1 day
    at a granularity of 15 minutes for a given stock symbol.

    Leverages the get_stock_data function for fetching and caching.

    Parameters:
        stock: The stock symbol (e.g., "AAPL", "MSFT").

    Returns:
        pandas.DataFrame | None: A DataFrame containing the 15-minute historical data
                                  for the specified period ("1d"), or None if data
                                  could not be fetched or an error occurred in
                                  the underlying get_stock_data call. Can return
                                  an empty DataFrame if yfinance provides one.
    """
    return get_stock_15m(stock).to_json()

@shared_task
def get_top_stock_india():
    """
    Function to return immediate stock data for top companies like nifty50
    """
    stocks = ('^NSEI', '^BSESN', 'RELIANCE.NS', 'TATAMOTORS.NS','NESTLEIND.NS',
              'DABUR.NS','WIPRO.NS','TECHM.NS','LICI.NS','ADANIENT.NS')
    response = {}
    # for idx, stock in enumerate(stocks):
    #     cache_key = f"stock_price_{stock}"
    #     cached_data = cache.get(cache_key)

    #     if (cached_data is not None and (not cached_data.empty)):
    #         response[stock] = cached_data.to_json()         
    #         continue

    #     ticker = yf.Ticker(stock)
    #     data = ticker.history(period="5d", interval="1h")
    #     try:
    #         current_close = data['Close']
    #         cache.set(cache_key, current_close, timeout=30000)
    #         response[stock] = current_close.to_json()

    #     except KeyError:
    #         continue
    # return response


    for idx, stock in enumerate(stocks):
        _ = idx
        logger.log("Fetching data for top india stock %s", stock)

        stock_data_dict = get_stock_data(stock=stock, period="5d", interval="1h",
                                         historyOnly=True)

        history_dict = stock_data_dict.get("history")

        if history_dict is None:
            logger.warning("get_stock_data returned None for history for %s", stock)

        elif history_dict.empty:
            logger.info("get_stock_data returned an empty DataFrame for history for %s", stock)

        else:
            current_close = history_dict["Close"]
            response[stock] = current_close.to_json()

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

# TODO: create a utility function to fetch data for a number of stocks and send them via SSE


# if __name__ == "__main__":
#     stock = "NVDA"
#     ticker = yf.Ticker(stock)
#     print(ticker.history(period = "1d", interval = "15m"))
#     information = ticker.info
#     keys = ["financialCurrency", "shortName", "website"]
#     for key in keys:
#         print(information[key])