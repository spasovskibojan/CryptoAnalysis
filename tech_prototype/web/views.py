from django.shortcuts import render, redirect
from django.contrib import messages
import os
import sys
import requests
from .facade import CryptoMarketFacade, wake_up_services

BASE_DIR_OF_DJANGO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR_OF_DJANGO)

DATA_DIR = os.path.join(BASE_DIR_OF_DJANGO, '..', 'data')
DATA_DIR = os.path.abspath(DATA_DIR)

# Instantiate Facade
market_facade = CryptoMarketFacade(DATA_DIR)

def refresh_database(request):
    try:
        market_facade.refresh_database()
        messages.success(request, "Database successfully updated! 🚀")
    except Exception as e:
        messages.error(request, f"Error: {e}")
    return redirect('index')

def index(request):
    # Wake up TA and FA services (Render free tier cold start)
    # DISABLED: Causing worker timeouts. Services wake up automatically on first API call.
    # wake_up_services()
    
    query = request.GET.get('q')
    
    if not query:
        title_text = "⭐ Market Leaders"
        display_coins = market_facade.get_market_leaders()
    else:
        title_text = f"Results for: {query}"
        display_coins = market_facade.search_coins(query)

    return render(request, 'index.html', {
        'coins': display_coins,
        'query': query or '',
        'title_text': title_text
    })

def detail(request, symbol):
    timeframe = request.GET.get('timeframe', '1m')
    
    context, error = market_facade.get_coin_details(symbol, timeframe)
    
    if error:
        return render(request, 'detail.html', {
            'symbol': symbol,
            'error': error
        })
    
    # LSTM Предвидување - Call external service
    ai_prediction_result = None
    ai_error = None
    
    predict_symbol = request.GET.get('predict_symbol')
    predict_date = request.GET.get('predict_date')
    
    if predict_symbol and predict_date:
        try:
            # Get LSTM service URL from environment variable
            lstm_url = os.environ.get('LSTM_SERVICE_URL', 'http://localhost:7860')
            
            # Call external LSTM service via HTTP
            response = requests.post(
                f"{lstm_url}/predict",
                json={
                    "symbol": predict_symbol,
                    "target_date": predict_date
                },
                timeout=120
            )
            
            if response.status_code == 200:
                ai_prediction_result = response.json()
            else:
                ai_error = f"LSTM Service Error: {response.status_code} - {response.text}"
            
        except requests.exceptions.Timeout:
            ai_error = "LSTM service timeout. Please try again."
        except requests.exceptions.ConnectionError:
            ai_error = "Cannot connect to LSTM service. Please try again later."
        except Exception as e:
            ai_error = str(e)
    
    # Додавање на LSTM резултати во context
    context['ai_prediction_result'] = ai_prediction_result
    context['ai_error'] = ai_error
        
    return render(request, 'detail.html', context)
