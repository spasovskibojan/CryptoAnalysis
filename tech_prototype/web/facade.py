import os
import json
import pandas as pd
import requests
import concurrent.futures
from datetime import datetime, timedelta
from .ai_service import get_sentiment_analysis, get_on_chain_data

# URL of the Technical Analysis Microservice
TA_SERVICE_URL = os.getenv("TA_SERVICE_URL", "http://localhost:8001")
# URL of the Fundamental Analysis Microservice
FA_SERVICE_URL = os.getenv("FA_SERVICE_URL", "http://localhost:8002")

try:
    from pipeline import run_pipeline
except ImportError:
    def run_pipeline():
        print("Pipeline script not found!")

def wake_up_services():
    """
    Wake up TA and FA services if they're sleeping (Render free tier).
    Makes parallel health check calls with generous timeout.
    Returns True if services respond, False otherwise.
    """
    def ping_service(url, name):
        try:
            print(f"DEBUG: Waking up {name} at {url}")
            response = requests.get(url, timeout=45)  # 45s for cold start
            print(f"DEBUG: {name} responded with status {response.status_code}")
            return True
        except Exception as e:
            print(f"DEBUG: {name} failed to wake: {str(e)}")
            return False
    
    # Ping both services in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        ta_future = executor.submit(ping_service, f"{TA_SERVICE_URL}/", "TA Service")
        fa_future = executor.submit(ping_service, f"{FA_SERVICE_URL}/sentiment/BTC-USD", "FA Service")
        
        # Wait for both to complete
        ta_ready = ta_future.result()
        fa_ready = fa_future.result()
    
    print(f"DEBUG: Services ready - TA: {ta_ready}, FA: {fa_ready}")
    return ta_ready or fa_ready  # At least one should be ready

class CryptoMarketFacade:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.famous_coins = [
            'BTC-USD', 'ETH-USD', 'XRP-USD', 'SOL-USD', 'BNB-USD',
            'ADA-USD', 'DOGE-USD', 'TRX-USD', 'AVAX-USD', 'LTC-USD'
        ]
        self.ta_cache = {
            "data": None,
            "last_update": None
        }

    def format_price(self, value):
        try:
            val = float(value)
            if val > 1.0:
                return f"{val:.2f}"
            return f"{val:.6f}"
        except:
            return "0.00"

    def get_coin_basic_info(self, symbol):
        file_path = os.path.join(self.data_dir, f"{symbol}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if data:
                        last = data[-1]
                        open_p = float(last.get('Open', 0))
                        close_p = float(last.get('Close', 0))
                        change = ((close_p - open_p) / open_p * 100) if open_p else 0
                        return {
                            'symbol': symbol,
                            'price': self.format_price(close_p),
                            'change_raw': change,
                            'change_str': f"{change:.2f}"
                        }
            except:
                return None
        return None

    def get_market_leaders(self):
        display_coins = []
        for symbol in self.famous_coins:
            coin = self.get_coin_basic_info(symbol)
            if coin:
                display_coins.append(coin)
        return display_coins

    def search_coins(self, query):
        display_coins = []
        if os.path.exists(self.data_dir):
            files = [f for f in os.listdir(self.data_dir) if f.endswith('.json')]
            for file in files:
                symbol = file.replace('.json', '')
                if query.lower() in symbol.lower():
                    coin = self.get_coin_basic_info(symbol)
                    if coin:
                        display_coins.append(coin)
        return display_coins

    def refresh_database(self):
        run_pipeline()

    def resample_df(self, df, timeframe):
        if timeframe == "1d":
            return df.copy()

        rule_map = {"1w": "W", "1m": "ME"}
        rule = rule_map.get(timeframe, "D")

        resampled = df.resample(rule, on="Date").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }).dropna().reset_index()
        
        return resampled

    def _call_ta_service(self, df):
        try:
            df_to_send = df.copy()

            if 'Date' not in df_to_send.columns:
                df_to_send = df_to_send.reset_index()

            if 'Datetime' in df_to_send.columns:
                df_to_send = df_to_send.rename(columns={'Datetime': 'Date'})

            df_to_send['Date'] = pd.to_datetime(df_to_send['Date'])
            df_to_send['Date'] = df_to_send['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')

            data_payload = df_to_send.to_dict(orient='records')

            print(f"DEBUG: Calling TA service at {TA_SERVICE_URL}/analyze")
            response = requests.post(f"{TA_SERVICE_URL}/analyze", json={"data": data_payload}, timeout=20)

            if response.status_code == 200:
                result = response.json()

                # NEW: support both old and new response formats
                if "overall_signal" in result:
                    return {
                        "overall_signal": result.get("overall_signal", "N/A"),
                        "overall_score": result.get("overall_score", 0),
                        "signals": result.get("signals", [])
                    }

                # OLD fallback:
                return {
                    "overall_signal": result.get("signal", "N/A"),
                    "overall_score": 0,
                    "signals": []
                }

            return {"overall_signal": "Error", "overall_score": 0, "signals": []}

        except Exception:
            return {"overall_signal": "Service Down", "overall_score": 0, "signals": []}

    def _get_sentiment_from_service(self, symbol):
        try:
            print(f"DEBUG: Calling FA sentiment at {FA_SERVICE_URL}/sentiment/{symbol}")
            r = requests.get(f"{FA_SERVICE_URL}/sentiment/{symbol}", timeout=20)
            if r.status_code == 200:
                return r.json()
        except:
            pass
        return None

    def _get_on_chain_from_service(self, symbol):
        try:
            print(f"DEBUG: Calling FA onchain at {FA_SERVICE_URL}/onchain/{symbol}")
            r = requests.get(f"{FA_SERVICE_URL}/onchain/{symbol}", timeout=20)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def get_coin_details(self, symbol, timeframe='1m'):
        file_path = os.path.join(self.data_dir, f"{symbol}.json")

        if not os.path.exists(file_path):
            return None, "File not found"

        try:
            with open(file_path, 'r') as f:
                raw_data = json.load(f)
        except:
            return None, "Invalid JSON"

        df = pd.DataFrame(raw_data)
        df['Date'] = pd.to_datetime(df['Date'])

        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = df[col].astype(float)

        end_date = df['Date'].max()

        if timeframe == '1y':
            start_date = end_date - timedelta(days=365)
        elif timeframe == '10y':
            start_date = end_date - timedelta(days=365 * 10)
        else:
            start_date = end_date - timedelta(days=30)

        mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
        filtered_df = df.loc[mask].copy()

        filtered_df['SMA_7'] = filtered_df['Close'].rolling(window=7).mean()
        filtered_df['EMA_7'] = filtered_df['Close'].ewm(span=7, adjust=False).mean()
        filtered_df = filtered_df.fillna(0)

        chart_dates = filtered_df['Date'].dt.strftime('%Y-%m-%d').tolist()
        chart_closes = filtered_df['Close'].tolist()
        chart_sma = filtered_df['SMA_7'].tolist()
        chart_ema = filtered_df['EMA_7'].tolist()

        sentiment_data = None
        on_chain_data = None

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # CALLING NEW MICROSERVICE METHODS
            future_sentiment = executor.submit(self._get_sentiment_from_service, symbol)
            future_on_chain = executor.submit(self._get_on_chain_from_service, symbol)

            try:
                sentiment_data = future_sentiment.result()
            except Exception as e:
                print(f"Sentiment error: {e}")

            try:
                on_chain_data = future_on_chain.result()
            except Exception as e:
                print(f"On-chain error: {e}")

        try:
            current_price = df['Close'].iloc[-1]
            realized_price_proxy = df['Close'].rolling(window=365).mean().iloc[-1]
            if pd.isna(realized_price_proxy):
                realized_price_proxy = df['Close'].mean()

            mvrv = current_price / realized_price_proxy if realized_price_proxy > 0 else 1.0

            if on_chain_data:
                on_chain_data['mvrv'] = f"{mvrv:.2f}"
        except:
            if on_chain_data:
                on_chain_data['mvrv'] = "1.25"

        ta_signals = {}  # just BUY/SELL/HOLD for the 3 cards
        ta_details = {}  # full response for tables

        for tf in ["1d", "1w", "1m"]:
            tf_df = self.resample_df(df, tf)

            if len(tf_df) < 50:
                ta_signals[tf] = "N/A"
                ta_details[tf] = {"overall_signal": "N/A", "overall_score": 0, "signals": []}
                continue

            result = self._call_ta_service(tf_df)

            ta_signals[tf] = result.get("overall_signal", "N/A")
            ta_details[tf] = result

        table_data = filtered_df.sort_values(by='Date', ascending=False).to_dict('records')
        for row in table_data:
            row['Date'] = row['Date'].strftime('%Y-%m-%d')
            if row['Open'] > 0:
                chg = ((row['Close'] - row['Open']) / row['Open']) * 100
                row['change_str'] = f"{chg:.2f}"
                row['change_raw'] = chg
            else:
                row['change_str'] = "0.00"
                row['change_raw'] = 0

        context = {
            'symbol': symbol,
            'timeframe': timeframe,
            'table_data': table_data,
            'chart_labels': json.dumps(chart_dates),
            'chart_closes': json.dumps(chart_closes),
            'chart_sma': json.dumps(chart_sma),
            'chart_ema': json.dumps(chart_ema),
            'sentiment': sentiment_data,
            'on_chain': on_chain_data,
            'ta_signals': ta_signals,
            'ta_details': ta_details
        }
        return context, None

    def compute_all_coin_signals(self):
        # Can also use microservice or cache here
        # For brevity, implementing similar loop
        # We can implement a bulk API endpoint later
        pass
