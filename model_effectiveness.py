from flask import Blueprint, request, jsonify
from progress_report import get_user_sessions, get_firestore_client, get_week_window_and_validate, get_empty_response
import re
import os
import asyncio
from functools import wraps
from openai import OpenAI
from dotenv import load_dotenv

model_effectiveness_bp = Blueprint('model_effectiveness', __name__)

# Load environment variables for Deepseek API
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-09e270ba6ccb42f9af9cbe92c6be24d8")
deepseek_client = OpenAI(
    base_url="https://api.deepseek.com/v1",
    api_key=DEEPSEEK_API_KEY
)
"""
import os
import openai
 
openai.api_key     = os.getenv("OPENROUTER_API_KEY")
openai.api_base    = "https://openrouter.ai/v1"
openai.api_type    = "openai"
openai.api_version = "v1"
"""
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

def get_effectiveness_from_deepseek(bot_name, session_messages):
    """Get effectiveness and rating from Deepseek analysis"""
    try:
        if not session_messages:
            print(f"No messages for {bot_name}")
            return None, None
            
        messages_text = "\n".join([
            msg.get('message', '') if isinstance(msg, dict) else str(msg) 
            for msg in session_messages
        ])[:1000]  # Limit text size
        
        if not messages_text.strip():
            print(f"No meaningful messages for {bot_name}")
            return None, None
        
        print(f"Analyzing {bot_name} session with {len(messages_text)} characters...")
        
        prompt = f"""
Analyze this therapy session with {bot_name} and provide:
1. Effectiveness score (0-100): How effective was this session?
2. User satisfaction rating (1-5): How satisfied would the user be?

Session content:
{messages_text}

Respond ONLY with two numbers separated by a comma (e.g., "75,4")
"""
        
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            max_tokens=10000,  # Fixed: use valid range [1, 8192]
            timeout=5 # Increased timeout to 10 seconds

        )
        
        result = response.choices[0].message.content.strip()
        print(f"Deepseek response for {bot_name}: {result}")
        
        match = re.search(r"(\d+),(\d+)", result)
        if match:
            effectiveness = int(match.group(1))
            rating = int(match.group(2))
            print(f"Extracted effectiveness: {effectiveness}, rating: {rating}")
            return effectiveness, rating
        else:
            print(f"Could not parse Deepseek response: {result}")
            
    except Exception as e:
        print(f"Deepseek analysis failed for {bot_name}: {e}")
    
    return None, None

@model_effectiveness_bp.route('/model_effectiveness', methods=['GET'])
def model_effectiveness():
    """Get AI model effectiveness metrics per bot/therapy type, filtered by user_id and/or bot_id if provided"""
    try:
        user_id = request.args.get('user_id')
        bot_id = request.args.get('bot_id')
        start_date = request.args.get('start_date')
        
        if not user_id and not bot_id:
            return jsonify({'error': 'user_id or bot_id is required'}), 400

        # Check weekly gating logic (if user_id is provided)
        if user_id:
            gating_result = get_week_window_and_validate(user_id, start_date)
            if not gating_result['valid']:
                return jsonify(get_empty_response('model_effectiveness')), 200

        sessions = get_user_sessions(user_id) if user_id else []
        
        # Filter sessions to the specific week (if user_id provided)
        if user_id and 'gating_result' in locals():
            from datetime import datetime, timedelta
            week_start = gating_result['week_start'].date()
            week_end = gating_result['week_end'].date()
            
            sessions_week = []
            for s in sessions:
                session_date = None
                if 'start_time' in s:
                    session_date = datetime.fromisoformat(s['start_time']).date()
                elif 'timestamp' in s:
                    try:
                        session_date = datetime.fromisoformat(s['timestamp']).date()
                    except:
                        pass
                elif 'messages' in s and s['messages'] and 'timestamp' in s['messages'][0]:
                    try:
                        session_date = datetime.fromisoformat(s['messages'][0]['timestamp']).date()
                    except:
                        pass
                if session_date and week_start <= session_date <= week_end:
                    sessions_week.append(s)
            sessions = sessions_week
        
        # If bot_id is provided, filter sessions by bot_id
        if bot_id:
            if not sessions:
                # If user_id not provided, fetch all sessions and filter by bot_id
                db = get_firestore_client()
                sessions_ref = db.collection('sessions').stream()
                sessions = [doc.to_dict() for doc in sessions_ref]
            sessions = [s for s in sessions if s.get('bot_id') == bot_id]

        # Aggregate data by bot_name
        bot_data = {}
        for session in sessions:
            bot_name = session.get('bot_name', 'Unknown')
            if not bot_name:
                continue
            if bot_name not in bot_data:
                bot_data[bot_name] = {
                    'session_count': 0,
                    'effectiveness': 0,
                    'ratings': [],
                    'sessions': []
                }
            
            # Use session_number if available, otherwise count sessions
            # session_number represents the total session count for this bot/user
            session_number = session.get('session_number', 1)
            bot_data[bot_name]['session_count'] = max(bot_data[bot_name]['session_count'], session_number)
            bot_data[bot_name]['sessions'].append(session)
            
            # Try to get effectiveness and rating from session data
            effectiveness = session.get('effectiveness')
            rating = session.get('rating')
            
            # If not available, use Deepseek analysis as fallback
            if effectiveness is None or rating is None:
                messages = session.get('messages', [])
                ds_effectiveness, ds_rating = get_effectiveness_from_deepseek(bot_name, messages)
                if effectiveness is None:
                    if ds_effectiveness is not None:
                        effectiveness = ds_effectiveness
                    else:
                        # Fallback: estimate based on message count and session completion
                        message_count = len(messages) if messages else 0
                        if message_count >= 10:
                            effectiveness = 75  # Good engagement
                        elif message_count >= 5:
                            effectiveness = 60  # Moderate engagement
                        elif message_count >= 2:
                            effectiveness = 45  # Basic engagement
                        else:
                            effectiveness = 30  # Minimal engagement
                            
                if rating is None:
                    if ds_rating is not None:
                        rating = ds_rating
                    else:
                        # Fallback: estimate based on effectiveness
                        if effectiveness >= 70:
                            rating = 4
                        elif effectiveness >= 50:
                            rating = 3
                        elif effectiveness >= 30:
                            rating = 2
                        else:
                            rating = 1
            
            # Add to aggregated data
            if effectiveness is not None:
                bot_data[bot_name]['effectiveness'] += effectiveness
            if rating is not None:
                bot_data[bot_name]['ratings'].append(rating)

        # Calculate averages and format response
        response = []
        for bot_name, data in bot_data.items():
            session_count = data['session_count']  # This is now the max session_number
            actual_sessions_processed = len(data['sessions'])  # Number of actual sessions processed
            
            # Calculate effectiveness percentage
            if actual_sessions_processed > 0 and data['effectiveness'] > 0:
                effectiveness = round(data['effectiveness'] / actual_sessions_processed, 1)
            else:
                effectiveness = 0
                
            # Calculate average rating
            if data['ratings']:
                avg_rating = round(sum(data['ratings']) / len(data['ratings']), 1)
            else:
                avg_rating = '--'
                
            response.append({
                'bot_name': bot_name,
                'session_count': session_count,  # Use the session_number from Firestore
                'effectiveness': f'{effectiveness}%',
                'avg_rating': avg_rating
            })
        return jsonify({'model_effectiveness': response})
    except Exception as e:
        return jsonify({'error': f'Failed to fetch model effectiveness: {str(e)}'}), 500

# Async version of model_effectiveness for use in combined_analytics
async def model_effectiveness_async(user_id=None, bot_id=None, start_date=None):
    """Async version of model effectiveness metrics per bot/therapy type"""
    try:
        if not user_id and not bot_id:
            return {'error': 'user_id or bot_id is required'}

        # Check weekly gating logic if user_id is provided
        if user_id:
            gating_result = await call_function_async(get_week_window_and_validate, user_id, start_date)
            if not gating_result['valid']:
                return await call_function_async(get_empty_response, 'model_effectiveness')

        # Get sessions using async helper
        sessions = await call_function_async(get_user_sessions, user_id) if user_id else []
        
        # If bot_id is provided, filter sessions by bot_id
        if bot_id:
            if not sessions:
                # If user_id not provided, fetch all sessions and filter by bot_id
                db = await call_function_async(get_firestore_client)
                sessions_ref = await call_function_async(lambda: list(db.collection('sessions').stream()))
                sessions = [doc.to_dict() for doc in sessions_ref]
            sessions = [s for s in sessions if s.get('bot_id') == bot_id]

        # Aggregate data by bot_name
        bot_data = {}
        for session in sessions:
            bot_name = session.get('bot_name', 'Unknown')
            if not bot_name:
                continue
            if bot_name not in bot_data:
                bot_data[bot_name] = {
                    'session_count': 0,
                    'effectiveness': 0,
                    'ratings': [],
                    'sessions': []
                }
            
            # Use session_number if available, otherwise count sessions
            # session_number represents the total session count for this bot/user
            session_number = session.get('session_number', 1)
            bot_data[bot_name]['session_count'] = max(bot_data[bot_name]['session_count'], session_number)
            bot_data[bot_name]['sessions'].append(session)
            
            # Try to get effectiveness and rating from session data
            effectiveness = session.get('effectiveness')
            rating = session.get('rating')
            
            # If not available, use Deepseek analysis as fallback
            if effectiveness is None or rating is None:
                messages = session.get('messages', [])
                ds_effectiveness, ds_rating = await call_function_async(
                    get_effectiveness_from_deepseek, bot_name, messages
                )
                if effectiveness is None:
                    if ds_effectiveness is not None:
                        effectiveness = ds_effectiveness
                    else:
                        # Fallback: estimate based on message count and session completion
                        message_count = len(messages) if messages else 0
                        if message_count >= 10:
                            effectiveness = 75  # Good engagement
                        elif message_count >= 5:
                            effectiveness = 60  # Moderate engagement
                        elif message_count >= 2:
                            effectiveness = 45  # Basic engagement
                        else:
                            effectiveness = 30  # Minimal engagement
                            
                if rating is None:
                    if ds_rating is not None:
                        rating = ds_rating
                    else:
                        # Fallback: estimate based on effectiveness
                        if effectiveness >= 70:
                            rating = 4
                        elif effectiveness >= 50:
                            rating = 3
                        elif effectiveness >= 30:
                            rating = 2
                        else:
                            rating = 1
            
            # Add to aggregated data
            if effectiveness is not None:
                bot_data[bot_name]['effectiveness'] += effectiveness
            if rating is not None:
                bot_data[bot_name]['ratings'].append(rating)

        # Calculate averages and format response
        response = []
        for bot_name, data in bot_data.items():
            session_count = data['session_count']  # This is now the max session_number
            actual_sessions_processed = len(data['sessions'])  # Number of actual sessions processed
            
            # Calculate effectiveness percentage
            if actual_sessions_processed > 0 and data['effectiveness'] > 0:
                effectiveness = round(data['effectiveness'] / actual_sessions_processed, 1)
            else:
                effectiveness = 0
                
            # Calculate average rating
            if data['ratings']:
                avg_rating = round(sum(data['ratings']) / len(data['ratings']), 1)
            else:
                avg_rating = '--'
                
            response.append({
                'bot_name': bot_name,
                'session_count': session_count,  # Use the session_number from Firestore
                'effectiveness': f'{effectiveness}%',
                'avg_rating': avg_rating
            })
        return {'model_effectiveness': response}
    except Exception as e:
        print(f"Async model effectiveness error: {e}")
        return {'error': f'Failed to fetch model effectiveness: {str(e)}'}
