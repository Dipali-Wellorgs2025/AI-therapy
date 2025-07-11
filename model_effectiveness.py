
from flask import Blueprint, request, jsonify
from progress_report import get_user_sessions, get_firestore_client
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
            return None, None
            
        messages_text = "\n".join([
            msg.get('message', '') if isinstance(msg, dict) else str(msg) 
            for msg in session_messages
        ])[:1000]  # Limit text size
        
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
            temperature=0.3,
            max_tokens=1000,  # Increased slightly for better accuracy
            timeout=5  # 5 second timeout to prevent hanging
        )
        
        result = response.choices[0].message.content.strip()
        match = re.search(r"(\d+),(\d+)", result)
        if match:
            effectiveness = int(match.group(1))
            rating = int(match.group(2))
            return effectiveness, rating
            
    except Exception as e:
        print(f"Deepseek analysis failed: {e}")
    
    return None, None

@model_effectiveness_bp.route('/model_effectiveness', methods=['GET'])
def model_effectiveness():
    """Get AI model effectiveness metrics per bot/therapy type, filtered by user_id and/or bot_id if provided"""
    try:
        user_id = request.args.get('user_id')
        bot_id = request.args.get('bot_id')
        if not user_id and not bot_id:
            return jsonify({'error': 'user_id or bot_id is required'}), 400

        sessions = get_user_sessions(user_id) if user_id else []
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
                if effectiveness is None and ds_effectiveness is not None:
                    effectiveness = ds_effectiveness
                if rating is None and ds_rating is not None:
                    rating = ds_rating
            
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
            effectiveness = round(data['effectiveness'] / actual_sessions_processed, 2) if actual_sessions_processed > 0 and data['effectiveness'] > 0 else 0
            avg_rating = round(sum(data['ratings']) / len(data['ratings']), 1) if data['ratings'] else '--'
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
async def model_effectiveness_async(user_id=None, bot_id=None):
    """Async version of model effectiveness metrics per bot/therapy type"""
    try:
        if not user_id and not bot_id:
            return {'error': 'user_id or bot_id is required'}

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
                if effectiveness is None and ds_effectiveness is not None:
                    effectiveness = ds_effectiveness
                if rating is None and ds_rating is not None:
                    rating = ds_rating
            
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
            effectiveness = round(data['effectiveness'] / actual_sessions_processed, 2) if actual_sessions_processed > 0 and data['effectiveness'] > 0 else 0
            avg_rating = round(sum(data['ratings']) / len(data['ratings']), 1) if data['ratings'] else '--'
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
