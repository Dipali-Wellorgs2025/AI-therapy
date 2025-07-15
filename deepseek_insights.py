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
    # PATCH: Use recommended filter syntax
    sessions_ref = db.collection('sessions').where('user_id', '==', user_id).stream()
    sessions = []
    for doc in sessions_ref:
        session_data = doc.to_dict()
        if session_data:
            # --- PATCH: Strip whitespace from bot_name if present ---
            if 'bot_name' in session_data and isinstance(session_data['bot_name'], str):
                session_data['bot_name'] = session_data['bot_name'].strip()
            # --- PATCH: Strip whitespace from sender in messages ---
            if 'messages' in session_data:
                for msg in session_data['messages']:
                    if isinstance(msg, dict) and 'sender' in msg and isinstance(msg['sender'], str):
                        msg['sender'] = msg['sender'].strip()
            sessions.append(session_data)
    return sessions

def store_insights(user_id, insights):
    db = get_firestore_client()
    db.collection('analytics').document(user_id).set(insights, merge=True)


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


def generate_clinical_insights_and_recommendations(user_id, messages_by_day):
    # Build transcript from all messages
    transcript = "\n".join([msg for msgs in messages_by_day.values() for msg in msgs])
    if not transcript:
        return {"progress_indicators": [], "progress_insights": []}
    prompt = """
You are a clinical analytics assistant. Based on the following transcript, generate two lists:
1. progress_indicators: 3-5 concise bullet points showing measurable progress or engagement.
2. progress_insights: 3-5 concise bullet points with clinical recommendations or insights.

Return a valid JSON object with keys "progress_indicators" and "progress_insights".

Transcript:
""" + transcript
    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=300
        )
        import json, re
        content = response.choices[0].message.content.strip()
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            content = match.group(0)
        insights = json.loads(content)
    except Exception:
        insights = {"progress_indicators": [], "progress_insights": []}
    return insights

def generate_structured_clinical_insights(messages_by_day):
    transcript = "\n".join([msg for msgs in messages_by_day.values() for msg in msgs])
    if not transcript:
        return {
            "risk_assessment": [],
            "therapeutic_effectiveness": [],
            "treatment_recommendations": []
        }
    prompt = """
You are a clinical analytics assistant. Based on the following transcript, generate three lists:
1. risk_assessment: 3-5 concise bullet points about risk factors or concerns.
2. therapeutic_effectiveness: 3-5 concise bullet points about therapy effectiveness.
3. treatment_recommendations: 3-5 concise bullet points with clinical recommendations.

Return a valid JSON object with keys "risk_assessment", "therapeutic_effectiveness", and "treatment_recommendations".

Transcript:
""" + transcript
    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=400
        )
        import json, re
        content = response.choices[0].message.content.strip()
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            content = match.group(0)
        insights = json.loads(content)
    except Exception:
        insights = {
            "risk_assessment": [],
            "therapeutic_effectiveness": [],
            "treatment_recommendations": []
        }
    return insights

def generate_insights_for_user(user_id):
    sessions = get_user_sessions(user_id)
    if not sessions:
        raise Exception(f"No sessions found for user {user_id}. Please check if there are any completed sessions for this user.")
    from collections import defaultdict
    messages_by_day = defaultdict(list)
    for session in sessions:
        messages = session.get('messages', [])
        for msg in messages:
            if isinstance(msg, dict):
                message_text = msg.get('message', '')
                timestamp = msg.get('timestamp', '')
                date_str = None
                # --- PATCH: Always use message timestamp if present and valid ---
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        date_str = dt.strftime('%Y-%m-%d')
                    except Exception as e:
                        print(f"[DEBUG] Failed to parse message timestamp: {timestamp} ({e})")
                        date_str = None
                # fallback: use session date if available and message timestamp is missing/invalid
                if not date_str and 'timestamp' in session:
                    try:
                        dt = datetime.fromisoformat(session['timestamp'])
                        date_str = dt.strftime('%Y-%m-%d')
                    except Exception as e:
                        print(f"[DEBUG] Failed to parse session timestamp: {session.get('timestamp')} ({e})")
                        date_str = None
                # --- PATCH: Log the date assignment for each message ---
                print(f"[DEBUG] Assigning message '{message_text}' to date: {date_str}")
                if message_text and date_str:
                    messages_by_day[date_str].append(message_text)
    if not messages_by_day:
        raise Exception(f"No messages found in sessions for user {user_id}")
    analytics = generate_analytics_from_messages(messages_by_day)
    clinical = generate_clinical_insights_and_recommendations(user_id, messages_by_day)
    structured_clinical = generate_structured_clinical_insights(messages_by_day)
    # Combine all analytics fields
    all_analytics = {
        "summary": analytics.get("summary", ""),
        "mood_scores": analytics.get("mood_scores", {}),
        "progress_indicators": clinical.get("progress_indicators", []),
        "progress_insights": clinical.get("progress_insights", []),
        "Clinical_insights and Recommendations": structured_clinical,
        "analysis_version": "2.0"
    }
    store_insights(user_id, all_analytics)
    return all_analytics

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
        # --- PATCH: handle tuple response ---
        if isinstance(result, tuple):
            response_obj = result[0]
        else:
            response_obj = result
        return response_obj.get_json()

def normalize_name(name):
    return name.strip().lower() if isinstance(name, str) else name

def analyze_model_effectiveness(user_id):
    sessions = get_user_sessions(user_id)
    bot_effectiveness = {}
    for session in sessions:
        bot_name = normalize_name(session.get('bot_name', ''))
        messages = session.get('messages', [])
        # Only analyze if there are messages for the bot
        bot_msgs = [m for m in messages if normalize_name(m.get('sender', '')) == bot_name]
        if not bot_msgs:
            print(f"[DEBUG] No messages for bot: {bot_name}")
            continue
        # ...existing effectiveness extraction logic...
        # Example:
        print(f"[DEBUG] Found {len(bot_msgs)} messages for bot: {bot_name}")
        # ...existing code...
