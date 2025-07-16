import os
from openai import OpenAI
from datetime import date, datetime, timedelta
from flask import Blueprint, request, jsonify
from firebase_admin import firestore

# Import helpers from progress_api if needed, or redefine here
from progress_api import get_user_sessions, get_total_time, get_daily_motivational_quote

combined_progress_bp = Blueprint('combined_progress', __name__)

@combined_progress_bp.route('/progress/combined', methods=['GET'])
def get_combined_progress():
    """
    Returns all progress data in a single API call:
    - progress (wellness streak, milestone message, etc.)
    - healing_journey (times showed up, time for yourself, day streak, mood checkins)
    - milestones (milestone progress, motivational quote in last milestone)
    Query param: user_id (required)
    """
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

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
    mood_checkins = 0
    for s in sessions:
        if 'mood' in s and s['mood']:
            mood_checkins += 1
        elif 'dailyLogs' in s:
            for log_data in s['dailyLogs'].values():
                if isinstance(log_data, dict) and 'mood' in log_data and log_data['mood']:
                    mood_checkins += 1
                    break
    healing_journey_data = {
        "times_showed_up": total_sessions,
        "time_for_yourself": f"{total_hours}h",
        "day_streak": hj_day_streak,
        "mood_checkins": mood_checkins
    }

    # --- Milestones logic ---
    wellness_streak = 0
    if all_session_dates:
        day_set = set(all_session_dates)
        today = date.today()
        latest = all_session_dates[-1]
        if (today - latest).days <= 1:
            current_day = latest
            while current_day in day_set:
                wellness_streak += 1
                current_day = current_day - timedelta(days=1)
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
            "target": 25,
        }
        ,
        {
            "quote": quote
        }

    ]
    return jsonify({
        "progress": progress_data,
        "healing_journey": healing_journey_data,
        "milestones": milestones
    })
