
from flask import Blueprint, request, jsonify
from firebase_admin import firestore
from datetime import datetime, timedelta
import os
from openai import OpenAI
from dotenv import load_dotenv

insights_bp = Blueprint('insights', __name__)

# Load environment variables (for API key)
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-09e270ba6ccb42f9af9cbe92c6be24d8")
deepseek_client = OpenAI(
    base_url="https://api.deepseek.com/v1",
    api_key=DEEPSEEK_API_KEY
)

def get_firestore_client():
    return firestore.client()

def get_user_sessions(user_id):
    db = get_firestore_client()
    # Use user_id directly from the document data
    sessions_ref = db.collection('sessions').where('user_id', '==', user_id).stream()
    sessions = []
    
    for doc in sessions_ref:
        session_data = doc.to_dict()
        if session_data:
            sessions.append(session_data)

    # Also check direct document IDs (as seen in Firebase)

    return sessions

def store_insights(user_id, insights):
    db = get_firestore_client()
    db.collection('analytics').document(user_id).set({'deepseek_insights': insights}, merge=True)


def generate_analytics_from_messages(messages_by_day):
    """
    messages_by_day: dict of {date_str: [msg1, msg2, ...]}
    Returns: dict with 'summary' and 'mood_scores' (per day)
    """
    summary_bullets = []
    mood_scores = {}
    for date_str, messages in messages_by_day.items():
        # Join messages for the dayf
        day_text = "\n".join(messages)
        prompt = f"""
You are a mental health analytics assistant. Given the following messages from a user's therapy session on {date_str}, estimate the user's overall mood for that day on a scale of 1 (very difficult) to 10 (excellent). Only output a single integer for the mood score.\n\nMessages:\n{day_text}\n\nMood score (1-10):
"""
        try:
            response = deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=5
            )
            score_str = response.choices[0].message.content.strip()
            # Extract integer mood score
            import re
            m = re.search(r"(\d+)", score_str)
            if m:
                mood_scores[date_str] = int(m.group(1))
        except Exception:
            continue
    # Also generate a summary for all messages
    all_text = "\n".join([msg for msgs in messages_by_day.values() for msg in msgs])
    prompt = f"""
You are a mental health analytics assistant. Given the following messages from a user's therapy sessions, generate a concise summary of the user's therapy progress, engagement patterns, and any notable trends or recommendations. Use a clinical, supportive tone.\n\nMessages:\n{all_text}\n\nSummary (3-5 bullet points):
"""
    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=200
        )
        summary = response.choices[0].message.content.strip()
    except Exception:
        summary = ""
    return {"summary": summary, "mood_scores": mood_scores}


def generate_insights_for_user(user_id):
    sessions = get_user_sessions(user_id)
    if not sessions:
        raise Exception(f"No sessions found for user {user_id}. Please check if there are any completed sessions for this user.")
    # Group messages by day
    from collections import defaultdict
    messages_by_day = defaultdict(list)
    for session in sessions:
        messages = session.get('messages', [])
        for msg in messages:
            if isinstance(msg, dict):
                message_text = msg.get('message', '')
                timestamp = msg.get('timestamp', '')
                # Try to parse date from timestamp
                date_str = None
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        date_str = dt.strftime('%Y-%m-%d')
                    except Exception:
                        pass
                if not date_str:
                    # fallback: use session date if available
                    if 'timestamp' in session:
                        try:
                            dt = datetime.fromisoformat(session['timestamp'])
                            date_str = dt.strftime('%Y-%m-%d')
                        except Exception:
                            date_str = None
                if message_text and date_str:
                    messages_by_day[date_str].append(message_text)
    if not messages_by_day:
        raise Exception(f"No messages found in sessions for user {user_id}")
    insights = generate_analytics_from_messages(messages_by_day)
    if not insights:
        raise Exception("Failed to generate insights from messages")
    store_insights(user_id, insights)
    return insights

@insights_bp.route('/generate_insights', methods=['POST'])
def generate_insights():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        sessions = get_user_sessions(user_id)
        if not sessions:
            return jsonify({'error': 'No sessions found'}), 404
            
        summary = generate_insights_for_user(user_id)
        if summary is None:
            return jsonify({'error': 'Failed to generate insights'}), 500
        
        return jsonify({'insights': summary})
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@insights_bp.route('/get_insights', methods=['GET'])
def get_insights():
    try:
        user_id = request.args.get('user_id')
        start_date = request.args.get('start_date')
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400

        # Check weekly gating logic
        from progress_report import get_week_window_and_validate, get_empty_response
        gating_result = get_week_window_and_validate(user_id, start_date)
        if not gating_result['valid']:
            return jsonify(get_empty_response('insights')), 200
            
        db = get_firestore_client()
        doc = db.collection('analytics').document(user_id).get()
        
        if not doc.exists:
            return jsonify({'error': 'No analytics found'}), 404
            
        data = doc.to_dict()
        insights = data.get('deepseek_insights', '')
        
        return jsonify({'insights': insights})
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# Async support
import asyncio
from functools import wraps

async def call_function_async(func, *args, **kwargs):
    """Helper to run synchronous functions in async context"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)

async def get_insights_async(user_id, start_date=None):
    """Async version of get_insights"""
    from flask import Flask
    app = Flask(__name__)
    query_string = f'user_id={user_id}'
    if start_date:
        query_string += f'&start_date={start_date}'
    with app.test_request_context(f'/get_insights?{query_string}'):
        result = get_insights()
        return result.get_json()
