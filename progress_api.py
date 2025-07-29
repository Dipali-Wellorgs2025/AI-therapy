import os
from openai import OpenAI
from datetime import date
from flask import Blueprint, request, jsonify
from firebase_admin import firestore
from datetime import datetime, timedelta
import asyncio


# Simple in-memory cache for daily quote
_daily_quote_cache = {"date": None, "quote": None}
"""
# Initialize DeepSeek client (ensure your API key is set in env or here)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-09e270ba6ccb42f9af9cbe92c6be24d8")
deepseek_client = OpenAI(base_url="https://api.deepseek.com/v1", api_key=DEEPSEEK_API_KEY)
"""


import os
import openai
 
openai.api_key     = os.getenv("OPENROUTER_API_KEY")
openai.api_base    = "https://openrouter.ai/v1"
openai.api_type    = "openai"
openai.api_version = "v1"

def get_daily_motivational_quote():
    today = date.today().isoformat()
    if _daily_quote_cache["date"] == today and _daily_quote_cache["quote"]:
        return _daily_quote_cache["quote"]
    prompt = "Generate a short, two-line motivational quote for therapy and self-growth."
    response = client.chat.completions.create(
        model="deepseek/deepseek-r1-0528-qwen3-8b:free",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=60,
        temperature=0.8
    )
    quote = response.choices[0].message.content.strip()
    _daily_quote_cache["date"] = today
    _daily_quote_cache["quote"] = quote
    return quote


progress_async_bp = Blueprint('progress_async', __name__)

def get_firestore_client():
    return firestore.client()

def parse_session_date(session):
    # Try to get session date from 'start_time', 'timestamp', or first message
    if 'start_time' in session:
        try:
            return datetime.fromisoformat(session['start_time']).date()
        except:
            pass
    if 'timestamp' in session:
        try:
            return datetime.fromisoformat(session['timestamp']).date()
        except:
            pass
    if 'messages' in session and session['messages'] and 'timestamp' in session['messages'][0]:
        try:
            return datetime.fromisoformat(session['messages'][0]['timestamp']).date()
        except:
            pass
    return None

def get_user_sessions(uid):
    db = get_firestore_client()
    sessions_ref = db.collection('sessions').stream()
    sessions = []
    for doc in sessions_ref:
        doc_id = doc.id
        if doc_id.startswith(uid + "_"):
            session = doc.to_dict()
            session['__doc_id'] = doc_id
            sessions.append(session)
    return sessions

def calculate_streak(dates):
    if not dates:
        return 0
    dates = sorted(set(dates))  # ascending order
    if len(dates) == 0:
        return 0
    max_streak = 1
    current_streak = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i-1]).days == 1:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 1
    return max_streak

def get_total_time(sessions):
    total_minutes = 0
    for s in sessions:
        try:
            # Check for duration in dailyLogs first
            duration_found = False
            if 'dailyLogs' in s:
                for date_key, log_data in s['dailyLogs'].items():
                    if isinstance(log_data, dict) and 'duration' in log_data:
                        duration = log_data['duration']
                        if duration and duration > 0:
                            total_minutes += duration
                            duration_found = True
            if not duration_found:
                if 'start_time' in s and 'end_time' in s:
                    start = datetime.fromisoformat(s["start_time"])
                    end = datetime.fromisoformat(s["end_time"])
                    total_minutes += (end - start).total_seconds() / 60
                elif 'duration' in s:
                    total_minutes += s['duration']
        except Exception:
            continue
    total_hours = int(total_minutes // 60)
    return total_hours

@progress_async_bp.route('/progress', methods=['GET'])
def get_progress():
    """
    Returns user's progress for the Achievements UI:
    - Wellness streak (consecutive days with sessions)
    - Times showed up (total sessions)
    - Time for yourself (total hours)
    Query param: user_id (required)
    """
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Fetch sessions from Firestore
    sessions = get_user_sessions(user_id)
    # Collect all unique message dates from all sessions
    all_message_dates = set()
    for s in sessions:
        if 'messages' in s:
            for msg in s['messages']:
                if 'timestamp' in msg:
                    try:
                        dt = datetime.fromisoformat(msg['timestamp']).date()
                        all_message_dates.add(dt)
                    except Exception:
                        pass
    all_session_dates = sorted(all_message_dates)
    # Calculate the current streak: only count if the latest session date is today or yesterday (no break)
    streak = 0
    if all_session_dates:
        day_set = set(all_session_dates)
        today = date.today()
        latest = all_session_dates[-1]
        # Only count streak if latest session is today or yesterday
        if (today - latest).days <= 1:
            current_day = latest
            while current_day in day_set:
                streak += 1
                current_day = current_day - timedelta(days=1)
    # Next milestone logic: 7 if streak < 7, else 14
    if streak < 7:
        next_milestone = 7
        milestone_message = "Keep going!"
    else:
        next_milestone = 14
        milestone_message = "A week of showing up!"

    return jsonify({
        "wellness_streak": streak,
        "wellness_streak_text": f"{streak} days of showing up for yourself",
        "milestone_message": milestone_message,
        "next_milestone": next_milestone,
        "next_milestone_message": f"Keep going! Next milestone at {next_milestone} days",
        "session_dates": [d.isoformat() for d in all_session_dates]
    })


@progress_async_bp.route('/healing_journey', methods=['GET'])
def get_healing_journey():
    """
    Returns user's healing journey stats:
    - Times showed up (total sessions)
    - Time for yourself (total hours)
    Query param: user_id (required)
    """
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    sessions = get_user_sessions(user_id)
    # Use max session_number for total_sessions (like /milestones)
    session_numbers = [s.get('session_number', 0) for s in sessions if 'session_number' in s]
    total_sessions = max(session_numbers) if session_numbers else 0
    total_hours = get_total_time(sessions)

    # Use unique message timestamp dates for day_streak (like /progress)
    all_message_dates = set()
    for s in sessions:
        if 'messages' in s:
            for msg in s['messages']:
                if 'timestamp' in msg:
                    try:
                        dt = datetime.fromisoformat(msg['timestamp']).date()
                        all_message_dates.add(dt)
                    except Exception:
                        pass
    all_session_dates = sorted(all_message_dates)
    # Use the same wellness_streak logic as /progress (only count if the latest session date is today or yesterday)
    day_streak = 0
    if all_session_dates:
        day_set = set(all_session_dates)
        today = date.today()
        latest = all_session_dates[-1]
        # Only count streak if latest session is today or yesterday
        if (today - latest).days <= 1:
            current_day = latest
            while current_day in day_set:
                day_streak += 1
                current_day = current_day - timedelta(days=1)

    # Count mood check-ins (sessions with a 'mood' field or mood in dailyLogs)
    mood_checkins = 0
    for s in sessions:
        if 'mood' in s and s['mood']:
            mood_checkins += 1
        elif 'dailyLogs' in s:
            for log_data in s['dailyLogs'].values():
                if isinstance(log_data, dict) and 'mood' in log_data and log_data['mood']:
                    mood_checkins += 1
                    break
    
    return jsonify({
        "times_showed_up": total_sessions,
        "time_for_yourself": f"{total_hours}h",
        "day_streak": day_streak,
        "mood_checkins": mood_checkins
    })



@progress_async_bp.route('/milestones', methods=['GET'])
def get_milestones():
    """
    Returns user's milestone progress and achievement status for:
    - Session count milestones
    - Mood check-in milestone
    - Streak milestone
    Query param: user_id (required)
    """
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    sessions = get_user_sessions(user_id)
    print('Session doc IDs for user', user_id, ':', [s['__doc_id'] for s in sessions])

    # 1. Session count: use max session_number
    session_numbers = [s.get('session_number', 0) for s in sessions if 'session_number' in s]
    total_sessions = max(session_numbers) if session_numbers else 0

    # 2. Collect all unique message dates for streaks and mood check-ins
    all_message_dates = set()
    mood_checkins = 0
    for s in sessions:
        # Collect all message dates
        if 'messages' in s:
            for msg in s['messages']:
                if 'timestamp' in msg:
                    try:
                        dt = datetime.fromisoformat(msg['timestamp']).date()
                        all_message_dates.add(dt)
                    except Exception:
                        pass
                # Mood check-in: if message has 'mood' field
                if 'mood' in msg and msg['mood']:
                    mood_checkins += 1
        # Also check top-level mood and dailyLogs for legacy support
        if 'mood' in s and s['mood']:
            mood_checkins += 1
        elif 'dailyLogs' in s:
            for log_data in s['dailyLogs'].values():
                if isinstance(log_data, dict) and 'mood' in log_data and log_data['mood']:
                    mood_checkins += 1
                    break

    # 3. Calculate wellness_streak using the same logic as /progress
    all_session_dates = sorted(all_message_dates)
    wellness_streak = 0
    if all_session_dates:
        day_set = set(all_session_dates)
        today = date.today()
        latest = all_session_dates[-1]
        # Only count streak if latest session is today or yesterday
        if (today - latest).days <= 1:
            current_day = latest
            while current_day in day_set:
                wellness_streak += 1
                current_day = current_day - timedelta(days=1)

    milestones = [
        {
            "title": "You Took the First Step",
            "description": "Started your first therapy session",
            "achieved": total_sessions >= 1,
            "progress": min(total_sessions, 1),
            "target": 1
        },
        {
            "title": "You're Showing Up Regularly",
            "description": "Completed 5 therapy sessions",
            "achieved": total_sessions >= 5,
            "progress": min(total_sessions, 5),
            "target": 5
        },
        {
            "title": "Committed to Growth",
            "description": "Completed 10 therapy sessions",
            "achieved": total_sessions >= 10,
            "progress": min(total_sessions, 10),
            "target": 10
        },
        {
            "title": "Checking In With Yourself",
            "description": "Logged your mood for 7 days",
            "achieved": mood_checkins >= 7,
            "progress": min(mood_checkins, 7),
            "target": 7
        },
        {
            "title": "Consistency Champion",
            "description": "Maintained a 30-day wellness streak",
            "achieved": wellness_streak >= 30,
            "progress": min(wellness_streak, 30),
            "target": 30
        },
        {
            "title": "Wellness Warrior",
            "description": "Completed 25 therapy sessions",
            "achieved": total_sessions >= 25,
            "progress": min(total_sessions, 25),
            "target": 25
        }
    ]
    # Add daily motivational quote
    quote = get_daily_motivational_quote()
    return jsonify({
        "milestones": milestones,
        "motivational_quote": quote
    })
