import requests
import yfinance as yf
import os
import json
from datetime import datetime, timedelta
from config import DATA_DIR, YEARS_BACK


def filter_1_get_tickers():
    """
    Враќа листа од 10 избрани криптовалути.
    """
    print("--> Филтер 1: Вчитување на избраните 10 криптовалути...")
    target_tickers = [
        "BTC-USD", "ETH-USD", "XRP-USD", "SOL-USD", "BNB-USD",
        "ADA-USD", "DOGE-USD", "TRX-USD", "AVAX-USD", "LTC-USD"
    ]
    print(f"    Вкупно {len(target_tickers)} валути за обработка.")
    return target_tickers


def filter_2_check_date(symbol):
    """
    Проверува дали имаме податоци и до кој датум.
    """
    file_path = os.path.join(DATA_DIR, f"{symbol}.json")

    start_date = None
    today = datetime.now().date()
    ten_years_ago = today - timedelta(days=365 * YEARS_BACK)

    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if data:
                    last_entry = data[-1]
                    last_date_str = last_entry.get('Date')
                    if last_date_str:
                        last_date_obj = datetime.strptime(last_date_str, '%Y-%m-%d').date()
                        start_date = last_date_obj + timedelta(days=1)
        except:
            start_date = None
    if start_date is None:
        start_date = ten_years_ago

    if start_date >= today:
        return (symbol, None)

    return (symbol, start_date.strftime('%Y-%m-%d'))


def filter_3_fetch_data(data_tuple):
    """
    Ги пополнува податоците што недостасуваат и зачувува во JSON фајл.
    """
    symbol, start_date_str = data_tuple

    if start_date_str is None:
        return f"SKIP: {symbol} е веќе ажуриран."

    file_path = os.path.join(DATA_DIR, f"{symbol}.json")

    try:
        ticker = yf.Ticker(symbol)

        df = ticker.history(start=start_date_str, interval="1d")

        if df.empty:
            return f"NO DATA: Нема податоци за {symbol}."

        df.reset_index(inplace=True)
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')

        df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

        new_data = df.to_dict('records')

        existing_data = []
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                try:
                    existing_data = json.load(f)
                except:
                    existing_data = []

        combined_data = existing_data + new_data

        with open(file_path, 'w') as f:
            json.dump(combined_data, f, indent=4)

        return f"SUCCESS: {symbol} (+{len(new_data)} денови)."

    except Exception as e:
        return f"ERROR: Проблем со {symbol}: {str(e)}"