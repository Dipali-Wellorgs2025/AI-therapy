# 📍 File: progress.py
# ✅ Count today's mood check-ins with detailed debugging
import os
from openai import OpenAI
from datetime import date, datetime, timedelta
from flask import Blueprint, request, jsonify
from firebase_admin import firestore
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

progress_async_bp = Blueprint('progress_async', __name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-09e270ba6ccb42f9af9cbe92c6be24d8")
deepseek_client = OpenAI(base_url="https://api.deepseek.com/v1", api_key=DEEPSEEK_API_KEY)

_daily_quote_cache = {"date": None, "quote": None}

def get_firestore_client():
    return firestore.client()

def get_daily_motivational_quote():
    today = date.today().isoformat()
    if _daily_quote_cache["date"] == today:
        return _daily_quote_cache["quote"]

    prompt = "Generate a short, two-line motivational quote for therapy and self-growth."
    response = deepseek_client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=60,
        temperature=0.8
    )

    quote = response.choices[0].message.content.strip()
    _daily_quote_cache["date"] = today
    _daily_quote_cache["quote"] = quote
    return quote

def get_user_sessions(uid):
    db = get_firestore_client()
    return [
        {**doc.to_dict(), '__doc_id': doc.id}
        for doc in db.collection('sessions').stream()
        if doc.id.startswith(uid + "_")
    ]

def get_total_time(sessions):
    total_minutes = 0
    for s in sessions:
        try:
            found = False
            if 'dailyLogs' in s:
                for log in s['dailyLogs'].values():
                    if isinstance(log, dict) and 'duration' in log:
                        total_minutes += log['duration']
                        found = True
            if not found:
                if 'start_time' in s and 'end_time' in s:
                    start = datetime.fromisoformat(s['start_time'])
                    end = datetime.fromisoformat(s['end_time'])
                    total_minutes += (end - start).total_seconds() / 60
                elif 'duration' in s:
                    total_minutes += s['duration']
        except:
            continue
    return int(total_minutes // 60)

def calculate_streak(dates):
    if not dates:
        return 0
    sorted_dates = sorted(set(dates))
    today = date.today()
    if (today - sorted_dates[-1]).days > 1:
        return 0
    streak = 0
    current_day = sorted_dates[-1]
    while current_day in sorted_dates:
        streak += 1
        current_day -= timedelta(days=1)
    return streak

def compute_progress_data(user_id):
    db = get_firestore_client()
    sessions = get_user_sessions(user_id)

    message_dates = set()
    session_numbers = [s.get('session_number', 0) for s in sessions if 'session_number' in s]

    for s in sessions:
        if 'messages' in s:
            for msg in s['messages']:
                if 'timestamp' in msg:
                    try:
                        message_dates.add(datetime.fromisoformat(msg['timestamp']).date())
                    except:
                        pass
        if 'timestamp' in s:
            try:
                message_dates.add(datetime.fromisoformat(s['timestamp']).date())
            except:
                pass

    # ✅ DEBUGGING: Enhanced mood check-in counting
    today = date.today()
    today_str = today.strftime("%d-%m-%Y")
    mood_checkins_today = 0
    
    logger.info("="*80)
    logger.info(f"STARTING MOOD CHECK-IN COUNT FOR USER: {user_id}")
    logger.info(f"TODAY'S DATE: {today_str}")
    
    try:
        # Get all check-in documents for this user
        checkin_docs = db.collection("recent-checkin").where("uid", "==", user_id).stream()
        total_docs = 0
        matches = 0
        
        for doc in checkin_docs:
            total_docs += 1
            data = doc.to_dict()
            
            logger.info("-"*60)
            logger.info(f"DOCUMENT ID: {doc.id}")
            logger.debug(f"FULL DOCUMENT DATA: {data}")
            
            # Check for date field with different capitalizations
            date_value = None
            date_keys = 'date'
            for key in date_keys:
                if key in data:
                    date_value = data[date]
                    logger.info(f"Found date field: {date} = {date_value} (type: {type(date_value)})")
                    break
            
            if date_value is None:
                logger.warning("No date field found in document. Available keys: " + ", ".join(data.date()))
                continue
                
            # Convert to comparable string format
            if isinstance(date_value, datetime):
                # Handle Firestore Timestamp
                date_str = date_value.strftime("%d-%m-%Y")
                logger.info(f"Converted timestamp to string: {date_str}")
            elif isinstance(date_value, str):
                # Handle string date
                date_str = date_value.strip()
                # Normalize separators
                date_str = date_str.replace('/', '-').replace('.', '-')
                logger.info(f"Normalized date string: {date_str}")
            else:
                logger.warning(f"Unsupported date type: {type(date_value)}")
                continue
                
            # Compare with today's date
            if date_str == today_str:
                mood_checkins_today += 1
                matches += 1
                logger.info("✅ DATE MATCHES TODAY!")
            else:
                logger.info(f"Date doesn't match: {date_str} != {today_str}")
        
        logger.info("="*60)
        logger.info(f"PROCESSED DOCUMENTS: {total_docs}")
        logger.info(f"MATCHES FOUND: {matches}")
        logger.info(f"TODAY'S MOOD CHECK-INS: {mood_checkins_today}")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"ERROR COUNTING MOOD CHECK-INS: {str(e)}", exc_info=True)
        mood_checkins_today = 0  # Reset to avoid incorrect counts

    streak = calculate_streak(message_dates)
    total_sessions = max(session_numbers) if session_numbers else len(sessions)
    total_hours = get_total_time(sessions)
    quote = get_daily_motivational_quote()

    return {
        "progress": {
            "wellness_streak": streak,
            "wellness_streak_text": f"{streak} days of showing up for yourself",
            "milestone_message": "A week of showing up!" if streak >= 7 else "Keep going!",
            "next_milestone": 14 if streak >= 7 else 7,
            "next_milestone_message": f"Keep going! Next milestone at {14 if streak >= 7 else 7} days",
            "session_dates": [d.isoformat() for d in sorted(message_dates)]
        },
        "healing_journey": {
            "times_showed_up": total_sessions,
            "time_for_yourself": f"{total_hours}h",
            "day_streak": streak,
            "mood_checkins": mood_checkins_today
        },
        "milestones": [
            {"title": "You Took the First Step", "achieved": total_sessions >= 1, "progress": min(total_sessions, 1), "target": 1},
            {"title": "You're Showing Up Regularly", "achieved": total_sessions >= 5, "progress": min(total_sessions, 5), "target": 5},
            {"title": "Committed to Growth", "achieved": total_sessions >= 10, "progress": min(total_sessions, 10), "target": 10},
            {"title": "Checking In With Yourself", "achieved": mood_checkins_today >= 1, "progress": min(mood_checkins_today, 1), "target": 1},
            {"title": "Consistency Champion", "achieved": streak >= 30, "progress": min(streak, 30), "target": 30},
            {"title": "Wellness Warrior", "achieved": total_sessions >= 25, "progress": min(total_sessions, 25), "target": 25}
        ],
        "motivational_quote": quote
    }

def update_user_progress(user_id):
    db = get_firestore_client()
    data = compute_progress_data(user_id)
    db.collection("users").document(user_id).update({
        "progress": data["progress"],
        "healing_journey": data["healing_journey"],
        "milestones": data["milestones"],
        "motivational_quote": data["motivational_quote"]
    })

@progress_async_bp.route('/progress', methods=['GET'])
def get_progress():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    return jsonify(compute_progress_data(user_id)['progress'])

@progress_async_bp.route('/healing_journey', methods=['GET'])
def get_healing():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    return jsonify(compute_progress_data(user_id)['healing_journey'])

@progress_async_bp.route('/milestones', methods=['GET'])
def get_milestones():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    data = compute_progress_data(user_id)
    return jsonify({"milestones": data["milestones"], "motivational_quote": data["motivational_quote"]})
