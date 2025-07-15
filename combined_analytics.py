from flask import Blueprint, request, jsonify
from model_effectiveness import model_effectiveness
import asyncio
import concurrent.futures
from functools import wraps
import time
from threading import Lock
from firebase_admin import firestore


combined_bp = Blueprint('combined', __name__)
def get_firestore_client():
    return firestore.client()

# Simple in-memory cache with TTL
_cache = {}
_cache_lock = Lock()
CACHE_TTL = 300  # 5 minutes

def get_from_cache(key):
    with _cache_lock:
        if key in _cache:
            data, timestamp = _cache[key]
            if time.time() - timestamp < CACHE_TTL:
                return data
            else:
                del _cache[key]
    return None

def set_cache(key, data):
    with _cache_lock:
        _cache[key] = (data, time.time())

def async_route(f):
    """Decorator to enable async support in Flask routes"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async function
            return loop.run_until_complete(f(*args, **kwargs))
        except Exception as e:
            print(f"Async route error: {e}")
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    return wrapper

async def call_function_async(func, *args, **kwargs):
    """Helper to run synchronous functions in async context"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)

def get_clinical_insights(user_id):
    db = get_firestore_client()
    doc = db.collection('analytics').document(user_id).get()
    if doc.exists:
        data = doc.to_dict()
        insights = data.get('clinical_insights_and_recommendations', {})
        # Ensure keys exist
        if not insights:
            insights = {"progress_indicators": [], "progress_insights": []}
        return insights
    else:
        # Always return empty structure if not found
        return {"progress_indicators": [], "progress_insights": []}

@combined_bp.route('/combined_analytics', methods=['GET'])
@async_route
async def combined_analytics():
    """
    Returns all analytics in one API using async parallel execution and caching:
    - clinical_overview
    - mood_trend_analysis  
    - session_bar_chart
    - session_heatmap
    - model_effectiveness
    - clinical_insights_and_recommendations (includes progress_indicators and progress_insights)
    Query params: user_id (required), bot_id (optional), start_date (optional, YYYY-MM-DD)
    """
    user_id = request.args.get('user_id')
    bot_id = request.args.get('bot_id')
    start_date = request.args.get('start_date')
    refresh_cache = request.args.get('refresh', 'false').lower() == 'true'
    
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Check weekly gating logic first (centralized check)
    from progress_report import get_week_window_and_validate, get_empty_response
    gating_result = get_week_window_and_validate(user_id, start_date)
    if not gating_result['valid']:
        # Return empty response for all analytics
        empty_response = {
            'clinical_overview': get_empty_response('clinical_overview'),
            'mood_trend_analysis': get_empty_response('mood_trend_analysis'),
            'session_bar_chart': get_empty_response('session_bar_chart'),
            'session_heatmap': get_empty_response('session_heatmap'),
            'model_effectiveness': get_empty_response('model_effectiveness'),
            'clinical_insights_and_recommendations': get_empty_response('insights')
        }
        return jsonify(empty_response)

    # Check cache first (unless refresh is requested)
    cache_key = f"analytics_{user_id}_{bot_id or 'all'}_{start_date or 'auto'}"
    if not refresh_cache:
        cached_result = get_from_cache(cache_key)
        if cached_result:
            return jsonify(cached_result)

    # Helper to extract JSON from a Flask Response or return as-is if already dict
    def extract_json(resp):
        if hasattr(resp, 'get_json'):
            try:
                return resp.get_json()
            except:
                return {}
        elif hasattr(resp, 'json'):
            try:
                return resp.json
            except:
                return {}
        elif isinstance(resp, dict):
            return resp
        elif hasattr(resp, 'data'):
            try:
                import json
                return json.loads(resp.data.decode('utf-8'))
            except:
                return {}
        else:
            return {}
    
    try:
        # Import the async functions from the modules
        from progress_report import clinical_overview_async, mood_trend_analysis_async, session_bar_chart_async, session_heatmap_async
        from deepseek_insights import get_insights_async, get_firestore_client
        from model_effectiveness import model_effectiveness_async
        
        db = get_firestore_client()
        analytics_doc = db.collection('analytics').document(user_id).get()
        analytics_data = analytics_doc.to_dict() if analytics_doc.exists else {}

        # Execute all async functions in parallel
        tasks = [
            clinical_overview_async(user_id, start_date),
            mood_trend_analysis_async(user_id, start_date),
            session_bar_chart_async(user_id, start_date),
            session_heatmap_async(user_id, start_date),
            model_effectiveness_async(user_id, bot_id, start_date),
            get_insights_async(user_id, start_date)
        ]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Extract results and handle any exceptions
        clinical = results[0] if isinstance(results[0], dict) else {}
        mood_trend = results[1] if isinstance(results[1], dict) else {}
        session_bar = results[2] if isinstance(results[2], dict) else {}
        session_heat = results[3] if isinstance(results[3], dict) else {}
        model_eff = results[4] if isinstance(results[4], dict) else {}
        get_insights_resp = results[5] if isinstance(results[5], dict) else {}
        
        # Debug: Print any exceptions that occurred
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Function {i} error: {result}")
            
    except Exception as e:
        return jsonify({'error': f'Failed to fetch analytics: {str(e)}'}), 500

    # Flatten nested keys for model_effectiveness and session_bar_chart
    model_effectiveness_data = model_eff.get('model_effectiveness') if isinstance(model_eff, dict) and 'model_effectiveness' in model_eff else model_eff
    session_bar_chart_data = session_bar.get('bar_chart') if isinstance(session_bar, dict) and 'bar_chart' in session_bar else session_bar
    session_insights_data = session_bar.get('session_insights') if isinstance(session_bar, dict) and 'session_insights' in session_bar else None

    # Flatten session_heatmap
    session_heatmap_data = session_heat.get('heatmap') if isinstance(session_heat, dict) and 'heatmap' in session_heat else session_heat
    usage_insights_data = session_heat.get('usage_insights') if isinstance(session_heat, dict) and 'usage_insights' in session_heat else None

    # Flatten mood_trend_analysis
    mood_trend_data = mood_trend.get('mood_trend') if isinstance(mood_trend, dict) and 'mood_trend' in mood_trend else mood_trend

    # Compose the response in the required flat structure
    response = {
        'clinical_overview': clinical,
        'mood_trend_analysis': mood_trend_data,
        'session_bar_chart': session_bar_chart_data,
        'session_insights': session_insights_data,
        'session_heatmap': session_heatmap_data,
        'usage_insights': usage_insights_data,
        'model_effectiveness': model_effectiveness_data,
        # Do NOT manually add clinical_insights_and_recommendations here
    }

    # --- PATCH: Add all analytics keys dynamically ---
    if analytics_data:
        for k, v in analytics_data.items():
            response[k] = v

    # Remove any None values to keep response clean
    response = {k: v for k, v in response.items() if v is not None}

    # Cache the result
    set_cache(cache_key, response)
    
    return jsonify(response)

@combined_bp.route('/clear_analytics_cache', methods=['POST'])
def clear_analytics_cache():
    """Clear the analytics cache - useful for testing or when fresh data is needed"""
    with _cache_lock:
        _cache.clear()
    return jsonify({'message': 'Analytics cache cleared successfully'})
    if analytics_data:
        for k, v in analytics_data.items():
            response[k] = v

    # Remove any None values to keep response clean
    response = {k: v for k, v in response.items() if v is not None}

    # Cache the result
    set_cache(cache_key, response)
    
    return jsonify(response)
