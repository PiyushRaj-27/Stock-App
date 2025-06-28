"""
Utility Functions for normal API working
"""
import re 
import os
import json
import time
import logging
from io import StringIO

import requests
from openai import OpenAI
import yfinance as yf
import pandas as pd
from pandas import DataFrame
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import User
from yfinance.exceptions import YFException
from celery import shared_task
from users.models import Customers

# OPENAI SPECIFIC CONFIGURATION
client = OpenAI(
    api_key=os.getenv("OPENAI_KEY"),
)

# DO NOT TOUCH POSITIVELY, CONTAIN THE FILE ID OF UPLOADED FILES
FILEIDS = {"stock_knowledge": "file-QkUr6JFJf7nq2Uw9uLXGur"}


logger = logging.getLogger(__name__)

HISTORY_TIMEOUT = 300000
INFO_TIMEOUT = 300000
PREDICTION_TIMEOUT = 14400


#PHONEPAY RELATED SETTINGS. DO NOT TOUCH POSITIVELY
PHONEPE_GRANT_TYPE = 'client_credentials'
PHONEPE_AUTH_URL = settings.PHONEPE_API_URL + "/v1/oauth/token"

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
        if historyOnly:
            history_json = cache.get(cache_key_history, "")
            history = pd.read_json(StringIO(history_json))
        elif informationOnly:
            info_json = cache.get(cache_key_info, "")
            info = json.loads(info_json)
        else:
            history_json = cache.get(cache_key_history, "")
            history = pd.read_json(StringIO(history_json))
            info_json = cache.get(cache_key_info, "")
            info = json.loads(info_json)

    except ConnectionError as e:
        logger.error("Connection to redis cache failed. Fallback to live: %s", e)

    except TimeoutError as e:
        logger.error("Redis took too long to response: %s", e)

    except Exception as e:
        logger.error("Cache get failed with exception. Fallback to live: %s", e)

    if (history is None or history.empty) and not informationOnly:
        logger.warning("Fetching live data for stock %s", stock)

        try:
            ticker = yf.Ticker(stock)
            history = ticker.history(period=period, interval=interval)

            try:
                print("setting cache")
                cache.set(cache_key_history, history.to_json(), timeout=HISTORY_TIMEOUT)

            except ConnectionError as e:
                logger.error("Connection to redis cache failed. Data cannot be cached: %s", e)

            except TimeoutError as e:
                logger.error("Redis took too long to response: %s", e)

            except Exception as e:
                logger.error("cache set failed: %s. Data cannot be cached", e)

        except YFException as e:
            logger.info("Failed to fetch history from Yfinance %s", e)
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
            logger.info("Failed to fetch history from Yfinance %s", e)
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
    stock_info_dict = get_stock_data(stock=stock, informationOnly=True)
    history_df = stock_data_dict.get("history")
    stock_info = stock_info_dict.get("info",{})
    if history_df is None:
        logger.warning("get_stock_data returned None for history for %s", stock)

    elif history_df.empty:
        logger.info("get_stock_data returned an empty DataFrame for history for %s", stock)

    return {"history": history_df, "info": stock_info}


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
    stock_all_info = get_stock_15m(stock)
    stock_history = stock_all_info.get("history")
    stock_info = stock_all_info.get("info")
    return {"data": stock_history.to_json(), "metadata": {"currency": stock_info.get("financialCurrency"), "status": stock_info.get("marketState"), 'volume': stock_info.get("volume",-1)}}

@shared_task
def get_top_stock_india():
    """
    Function to return immediate stock data for top companies like nifty50
    """
    stocks = ('^NSEI', '^BSESN', 'RELIANCE.NS', 'TATAMOTORS.NS','NESTLEIND.NS',
              'DABUR.NS','WIPRO.NS','TECHM.NS','LICI.NS','ADANIENT.NS')
    response = {}

    for idx, stock in enumerate(stocks):
        _ = idx
        logger.info("Fetching data for top india stock %s", stock)

        stock_data_dict = get_stock_data(stock=stock, period="5d", interval="1h",
                                         historyOnly=True)

        history_dict = stock_data_dict.get("history")

        stock_info_dict = get_stock_data(stock=stock, informationOnly=True)

        information_dict = stock_info_dict.get("info")
        currency = information_dict.get("financialCurrency")
        real_name = information_dict.get("shortName")
        if history_dict is None:
            logger.warning("get_stock_data returned None for history for %s", stock)

        elif history_dict.empty:
            logger.info("get_stock_data returned an empty DataFrame for history for %s", stock)

        else:
            current_close = history_dict["Close"]
            response[stock] = {'data': current_close.to_json(), 'real_name': real_name, 'currency' : currency}

    return response


def get_currency_stock(stock: str):
    """
    Returns the currency value of a given stock
    """

    data = get_stock_data(stock, informationOnly=True)
    data = data.get("info", {})
    return data.get("financialCurrency", "")
    # print(data)


def parse_yfinance_news(api_response):
    """
    Parses the Yahoo Finance API news response into a list of dictionaries.

    Args:
        api_response (list): A list of dictionaries, where each dictionary
                             represents a news item from the yfinance API.

    Returns:
        list: A list of dictionaries, each with 'Title', 'desc', and 'time' keys.
    """
    parsed_articles = []
    for item in api_response:
        content = item.get('content')
        if not content: # Should not happen with valid input, but good practice
            continue

        title = content.get('title', 'N/A') # Default if title is missing

        # Prioritize summary, then description for 'desc'
        description = content.get('summary')
        if not description: # If summary is None or an empty string
            description = content.get('description', '') # Fallback to description

        # Simple HTML tag removal from description
        # This removes content between < and >
        cleaned_description = re.sub(r'<[^>]+>', '', description)
        # Replace non-breaking space HTML entity if any are left
        cleaned_description = cleaned_description.replace(' ', ' ').strip()


        pub_date = content.get('pubDate', 'N/A') # Default if pubDate is missing

        parsed_articles.append({
            'Title': title,
            'desc': cleaned_description,
            'time': pub_date
        })
    return parsed_articles


def fetch_stock_news(ticker: str, count: int = 5) -> list:
    """
    Fetches the latest news for a given stock ticker using yfinance.

    Parameters:
        ticker (str): The stock ticker symbol (e.g., 'AAPL', 'GOOG').
        count (int): Number of latest news items to return.

    Returns:
        List of dictionaries containing title, link, and publisher of each news item.
    """
    try:
        stock = yf.Ticker(ticker)
        news = stock.news[:count]
        # Clean and format results
        return parse_yfinance_news(news)
    except Exception as e:
        print(f"Error fetching news for {ticker}: {e}")
        return []

def call_openai_prediction(prompt: str, model:str = "gpt-4o") -> dict:
    """
    Utility function to call chatgpt API for prediction.
    
    Parameter:
        prompt: prompt which is sent as the user along with the system prompt
        model: which model to call on openai API
    
    Returns:
        The completed chat from openai
    """
    result =  {"response":"", "error": False, "message": ""}
    try:
        response = client.responses.create(
            model=model,
            instructions="""
                    -Predict tomorrow closing price for this company using the given this month' closing prices and chart patterns. 
                    
                    -Be precise and restrict the closing range to exactly 2-3 rupees

                    -Incase of international company, restrict the closing range to exactly 2-3 dollars.

                    -Be precise and provide a tight range.

                    -Output format: 
                    High: (price)
                    Low: (price)
                    Sentiment : positive/ negative
                    Closing range: lowerBound-UpperBound

                    -Only give output in the given format with no further explanations and texts

                    -If you fail to give predictions, just give <no data available> as output, in that case            
            """,
            input=prompt,
        )

        result["response"] = response.output_text
        logger.info("LLM generated Response: %s", result["response"])
    except Exception as e:
        logger.warning("ChatGPT API error: %s" , e)
        result["error"] = True
        result["message"] = "Inference Failed"

    return result

def flatten_news_for_sentiment(news_list):
    """
    Converts a list of news dictionaries into a flattened, clean string suitable for LLM sentiment analysis.
    Each item includes the Title, Description, and optionally, Timestamp (if needed).
    """
    flattened = ""
    for i, news in enumerate(news_list, 1):
        title = news.get('Title', '').strip()
        desc = news.get('desc', '').strip()
        time = news.get('time', '').strip()
        flattened += f"News {i}:\nTitle: {title}\nDescription: {desc}\nDate: {time}\n\n"
    return flattened.strip()

def flatten_closing_prices(stock_history_df):
    """
    Extracts and flattens the 'Close' prices from a yfinance DataFrame.

    Parameters:
        stock_history_df (pd.DataFrame): DataFrame returned by yfinance.Ticker(...).history(...)

    Returns:
        list: A list of closing prices (floats), ordered by date ascending (oldest to newest).
    """
    try:
        if stock_history_df is None or 'Close' not in stock_history_df.columns:
            return []
        
        # Drop NaNs and extract close prices
        closing_prices = stock_history_df['Close'].dropna().tolist()
        return closing_prices
    except Exception as e:
        logger.error("Error flattening closing prices: %s", e)
        return []

def construct_prediction_prompt(stock_name: str, closing_prices: list, news_text: str) -> str:
    """
    Constructs a detailed prompt including stock name, recent 30-day closing prices, and latest news
    for use in LLM-based prediction.

    Parameters:
        stock_name (str): The name or ticker of the stock.
        closing_prices (list): A list of closing prices for the past 30 days.
        news_text (str): Flattened news string, cleaned for LLM use.

    Returns:
        str: A formatted prompt string ready to be passed to call_openai_prediction().
    """

    prompt = f"""
        Stock: {stock_name}
        Last 30 Days Closing Prices: {closing_prices}

        Relevant News:
        {news_text}
    """.strip()

    return prompt

def parse_llm_response(response: str) -> dict:
    """
    Parses the response coming from the llm.

    Parameters:
        response: The response recieved from the llm

    Returns:
        dict: Dictionary containing various attributes coming from the llm
    """

    expected_keys = ['High', 'Low', 'Sentiment', 'Closing range']
    result = {}

    lines = response.strip().split('\n')

    if len(lines) != 4:
        raise ValueError("Invalid format: Exactly 4 lines required.")

    for i, expected_key in enumerate(expected_keys):
        line = lines[i]

        # Ensure there's exactly one colon
        if line.count(':') != 1:
            raise ValueError(f"Line {i+1} must contain exactly one colon: '{line}'")

        key, value = map(str.strip, line.split(':'))

        if key != expected_key:
            raise ValueError(f"Expected key '{expected_key}', but found '{key}'")

        if key in ['High', 'Low']:

            result[key.lower()] = float(value)

        elif key == 'Sentiment':
            if not value:
                raise ValueError("Sentiment value cannot be empty.")
            result['sentiment'] = value
        elif key == 'Closing range':
            if value.count('-') != 1:
                raise ValueError("Closing Range must contain exactly one hyphen.")
            start_str, end_str = map(str.strip, value.split('-'))
            start = float(start_str)
            end = float(end_str)
            result['closingRange'] = {'start': start, 'end': end}

    return result


@shared_task
def make_prediction(stock: str, email):
    """ 
    Gives predicted value for a particular symbol.
        
    """

    # check if the customer has enough credit point or not
    user = User.objects.get(email =  email)
    customer = Customers.objects.get(user = user)
    if customer:
        if customer.credit_points < 1:
            return {"result": "" , "success": False, "message": "Insufficient credits. Purchase More credits to Get More Prediction"}


        # we can call the chatgpt API here but we need few things before taht
        # 1. stock data 
        # 2. News?
        # 3. Prompt format
        cache_key = f"app_prediction_{stock}"
        data = cache.get(cache_key)
        if data is not None:
            customer.credit -= 1
            customer.save()
            return json.loads(data)

        stock_data = get_stock_data(stock, period="1mo", interval='1d',historyOnly=True).get("history")
        if stock_data is None or stock_data.empty:
            logger.error("Unable to obatin stock data from YF api")
            return {"result":"", "success": False, "message": "API inference failed! Please Try again later"}


        try:
            news = flatten_news_for_sentiment(fetch_stock_news(stock, 5))
        except Exception as e:
            logger.error("Parsing News failed for stock %s with error %s", stock, e)
            news = "News Not Available for stock. Make predicions solely based on the closing price of the stock"

        try:
            stock_data_str = flatten_closing_prices(stock_data)
        except Exception as e:
            logger.error("Parsing Stock Price failed for stock %s with error %s", stock, e)
            return {"result":"", "success": False, "message": "API inference failed! Please Try again later"}

        prompt = construct_prediction_prompt(stock, closing_prices= stock_data_str, news_text= news)

        result = call_openai_prediction(prompt=prompt)
        if result["error"]:
            return {"result":"","success": False, "message":  "API inference failed! Please Try again later"}

        # TODO: check the formate of the response before deducting the credit points, otherwise on frontend things would go wavy....

        try:
            parsedResponse = parse_llm_response(result.get("response",""))

        except ValueError as e:
            logger.error("Parsing llm output failed with error: %s", e)
            return {"result":"","success": False, "message":  "API inference failed! Please Try again later"}

        toReturn = {"result":parsedResponse, "success": True, "message":"Success"}
        cache.set(cache_key, json.dumps(toReturn), timeout= PREDICTION_TIMEOUT)
        customer.credit -= 1
        customer.save()
        return toReturn

    return {"result": "" , "success": False, "message": "Unauthorized user"}

# TODO: create a utility function to fetch data for a number of stocks and send them via SSE



def get_phonepay_token():
    """
    Fetches auth token for payment initiation from phonepay

    returns:
        auth_token
    
    raises:
        Exception
    """

    cache_key = "phonepay_auth_token"
    data = cache.get(cache_key)

    if data is not None:
        logger.info("auth_key fetched from cache")
        return data

    logger.warning("phonepe_auth token fetch failed from cache. Refreshing token!")
    auth_payload = {
            'client_id': os.getenv("PHONEPAY_CLIENT_ID"),
            'client_secret': os.getenv("PHONEPAY_CLIENT_SECRET"),
            'grant_type': PHONEPE_GRANT_TYPE,
            'client_version': os.getenv("PHONEPAY_CLIENT_VER")
        }
    auth_headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:

        auth_response = requests.post(
            url=PHONEPE_AUTH_URL,
            data=auth_payload,
            headers=auth_headers,
            timeout= 100
        )

        auth_response.raise_for_status() # Raise an exception for bad status codes
        auth_data = auth_response.json()
        access_token = auth_data.get('access_token')
        issued_at = auth_data.get("issued_at")
        expires_at = auth_data.get("expires_at")

        if not access_token:
            raise Exception("Invalid response from auth server")

        cache.set(cache_key, access_token, expires_at - issued_at - 30) # early expire the token

        return access_token
    except Exception as e:
        logger.error("Access_token fetch failed with error %s", e)
        raise


def phonepe_check_order_status(merchantOrderId):
    """
    Implements phonepe order status API
    """
    url = settings.PHONEPE_API_URL + f"/checkout/v2/order/{merchantOrderId}/status"

    try:
        auth_token = get_phonepay_token()
        status_header = {
            "Content-Type": "application/json",
            "Authorization" : f"O-Bearer {auth_token}"
        }

        status_response = requests.get(
            url= url,
            headers=status_header,
            timeout=100
        )
        status_response.raise_for_status()
        status_data = status_response.json()
        success = status_data.get("success", True)
        if not success:
            logger.error("Invalid Merchant id %s", str(merchantOrderId))
            return "ERROR"

        status = status_data.get("state")
        return status

    except Exception as e:
        logger.error("Fetching order status for order id %s failed with error %s", str(merchantOrderId), e)
        return "ERROR"

@shared_task
def phonepe_order_check_celery(merchantOrderId):
    """
    Celery wrapper for phonepe order status api
    """
    state = phonepe_check_order_status(merchantOrderId)
    retry_count = 0
    while state == "PENDING" and retry_count < 10:
        time.sleep(2)
        retry_count += 1
        state = phonepe_check_order_status(merchantOrderId=merchantOrderId)

    return state