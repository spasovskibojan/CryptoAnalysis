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

# Global state to track service readiness
_service_status = {
    'ta_ready': False,
    'fa_ready': False,
    'wakeup_in_progress': False,
    'last_wakeup_attempt': None
}

def get_service_status():
    """Get current status of microservices."""
    return _service_status.copy()

def wake_up_services_async():
    """
    Wake up TA and FA services by triggering a single request, then waiting.
    Strategy: Send one wake-up ping (triggers Render to boot), wait 60s, check once.
    This avoids Render's rate limiting (429 errors) from excessive retries.
    """
    global _service_status
    import threading
    import time
    
    # Prevent multiple simultaneous wake-up attempts
    if _service_status['wakeup_in_progress']:
        print("DEBUG: Wake-up already in progress, skipping...", flush=True)
        return
    
    # If services were woken recently (within 5 minutes), skip
    if _service_status['last_wakeup_attempt']:
        from datetime import datetime, timedelta
        time_since_last = datetime.now() - _service_status['last_wakeup_attempt']
        if time_since_last < timedelta(minutes=5):
            print(f"DEBUG: Services were woken {time_since_last.seconds}s ago, skipping...", flush=True)
            return
    
    def trigger_and_wait(url, name, status_key, wait_time=60):
        """
        Trigger service wake-up with one request, wait for boot time, then verify.
        wait_time: seconds to wait before checking (default 60s for Render free tier)
        """
        print(f"DEBUG: Triggering wake-up for {name}...", flush=True)
        
        # Step 1: Send initial wake-up trigger (this starts Render's boot process)
        try:
            requests.get(url, timeout=5)
            print(f"DEBUG: Wake-up request sent to {name}", flush=True)
        except:
            # Expected - service is asleep and will start booting now
            print(f"DEBUG: {name} is booting (expected behavior)...", flush=True)
        
        # Step 2: Wait for service to fully boot
        print(f"DEBUG: Waiting {wait_time}s for {name} to boot...", flush=True)
        time.sleep(wait_time)
        
        # Step 3: Verify service is ready with one final health check
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"DEBUG: ✓ {name} is READY!", flush=True)
                _service_status[status_key] = True
                return True
            else:
                print(f"DEBUG: ✗ {name} responded with {response.status_code} (may need more time)", flush=True)
                return False
        except Exception as e:
            print(f"DEBUG: ✗ {name} health check failed: {e}", flush=True)
            return False
    
    def wake_all_services():
        global _service_status
        from datetime import datetime
        
        _service_status['wakeup_in_progress'] = True
        _service_status['last_wakeup_attempt'] = datetime.now()
        
        print("DEBUG: ========================================", flush=True)
        print("DEBUG: Starting service wake-up sequence...", flush=True)
        print("DEBUG: Strategy: Trigger once, wait 60s, verify once", flush=True)
        print("DEBUG: ========================================", flush=True)
        
        # Wake both services in parallel
        # Using root endpoint (/) instead of /health because it reliably triggers Render's wake-up
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            ta_future = executor.submit(
                trigger_and_wait, 
                f"{TA_SERVICE_URL}/", 
                "TA Service",
                "ta_ready",
                60  # Wait 60 seconds for boot
            )
            fa_future = executor.submit(
                trigger_and_wait, 
                f"{FA_SERVICE_URL}/", 
                "FA Service",
                "fa_ready",
                60  # Wait 60 seconds for boot
            )
            
            # Wait for both to complete
            ta_success = ta_future.result()
            fa_success = fa_future.result()
        
        _service_status['wakeup_in_progress'] = False
        
        if ta_success and fa_success:
            print("DEBUG: ✓✓✓ All services are READY! ✓✓✓", flush=True)
        else:
            print("DEBUG: ⚠ Some services did not respond", flush=True)
            print(f"DEBUG:   - TA Service: {'✓ Ready' if ta_success else '✗ Not Ready'}", flush=True)
            print(f"DEBUG:   - FA Service: {'✓ Ready' if fa_success else '✗ Not Ready'}", flush=True)
        
        print("DEBUG: ========================================", flush=True)
    
    # Run in background thread
    threading.Thread(target=wake_all_services, daemon=True).start()
    print("DEBUG: Wake-up thread started in background", flush=True)

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
        print(f"DEBUG: get_coin_details START for {symbol}", flush=True)
        file_path = os.path.join(self.data_dir, f"{symbol}.json")

        if not os.path.exists(file_path):
            print(f"DEBUG: File not found: {file_path}", flush=True)
            return None, "File not found"

        try:
            with open(file_path, 'r') as f:
                raw_data = json.load(f)
            print(f"DEBUG: JSON loaded, {len(raw_data)} records", flush=True)
        except Exception as e:
            print(f"DEBUG: JSON load error: {e}", flush=True)
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
