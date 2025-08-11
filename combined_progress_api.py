import os
from openai import OpenAI
from datetime import date, datetime, timedelta
from flask import Blueprint, request, jsonify
from firebase_admin import firestore

# Import helpers from progress_api if needed
from progress_api import get_user_sessions, get_total_time, get_daily_motivational_quote

combined_progress_bp = Blueprint('combined_progress', __name__)

# ---------------- Helper: Get today's mood check-in count ----------------
def get_today_mood_checkins(user_id):
    db = firestore.client()
    checkins_ref = db.collection("recent-checkin")

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())

    docs = checkins_ref.where("uid", "==", user_id).stream()

    count = 0
    for doc in docs:
        data = doc.to_dict()
        doc_date = data.get("date")

        if isinstance(doc_date, datetime):
            if today_start <= doc_date <= today_end:
                count += 1
        elif isinstance(doc_date, str):
            if doc_date == date.today().strftime("%d-%m-%Y"):
                count += 1

    return count  # Always an int, never None

# ---------------- API Route ----------------
@combined_progress_bp.route('/progress/combined', methods=['GET'])
def get_combined_progress():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Fetch user sessions
    sessions = get_user_sessions(user_id)

    # --- Progress logic ---
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

    streak = 0
    if all_session_dates:
        day_set = set(all_session_dates)
        today = date.today()
        latest = all_session_dates[-1]
        if (today - latest).days <= 1:
            current_day = latest
            while current_day in day_set:
                streak += 1
                current_day = current_day - timedelta(days=1)

    if streak < 7:
        next_milestone = 7
        milestone_message = "Keep going!"
    else:
        next_milestone = 14
        milestone_message = "A week of showing up!"

    progress_data = {
        "wellness_streak": streak,
        "wellness_streak_text": f"{streak} days of showing up for yourself",
        "milestone_message": milestone_message,
        "next_milestone": next_milestone,
        "next_milestone_message": f"Keep going! Next milestone at {next_milestone} days",
    }

    # --- Healing Journey logic ---
    session_numbers = [s.get('session_number', 0) for s in sessions if 'session_number' in s]
    total_sessions = max(session_numbers) if session_numbers else 0
    total_hours = get_total_time(sessions)

    hj_day_streak = 0
    if all_session_dates:
        day_set = set(all_session_dates)
        today = date.today()
        latest = all_session_dates[-1]
        if (today - latest).days <= 1:
            current_day = latest
            while current_day in day_set:
                hj_day_streak += 1
                current_day = current_day - timedelta(days=1)

    # Mood check-ins count for **today only**
    mood_checkins = get_today_mood_checkins(user_id)

    healing_journey_data = {
        "times_showed_up": total_sessions,
        "time_for_yourself": f"{total_hours}h",
        "day_streak": hj_day_streak,
        "mood_checkins": "mood_checkins"
    }

    # --- Milestones logic ---
    wellness_streak = streak
    quote = get_daily_motivational_quote()

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
            "achieved": mood_checkins >= 7,  # Updated to use today's check-ins if needed
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
            "target": 25,
        },
        {
            "quote": quote
        }
    ]

    return jsonify({
        "progress": progress_data,
        "healing_journey": healing_journey_data,
        "milestones": milestones
    })
