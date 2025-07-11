
from flask import Blueprint, request, jsonify
from firebase_admin import firestore
from datetime import datetime, timedelta
import calendar
import io
import base64
import asyncio
from functools import wraps

progress_bp = Blueprint('progress', __name__)


# --- Clinical Overview Endpoint (REAL DATA) ---
@progress_bp.route('/clinical_overview', methods=['GET'])
def clinical_overview():
    """
    Returns clinical overview metrics as shown in the UI:
    - Therapy Sessions
    - Mood Entries
    - Day Streak
    - Total Time (in hours)
    Query params: user_id (required)
    """
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # --- Fetch sessions from Firestore ---
    sessions = get_user_sessions(user_id)

    # --- Fetch moods from analytics collection (deepseek_insights) ---
    db = get_firestore_client()
    moods = []
    analytics_doc = db.collection('analytics').document(user_id).get()
    if analytics_doc.exists:
        data = analytics_doc.to_dict()
        insights = data.get('deepseek_insights', None)
        # Try to extract mood scores from insights
        if isinstance(insights, dict) and 'mood_scores' in insights:
            for date, score in insights['mood_scores'].items():
                moods.append({'user_id': user_id, 'date': date, 'score': score})
        elif isinstance(insights, str):
            import re
            for line in insights.split('\n'):
                m = re.match(r"Mood on (\d{4}-\d{2}-\d{2}): (\d+)", line)
                if m:
                    date, score = m.group(1), int(m.group(2))
                    moods.append({'user_id': user_id, 'date': date, 'score': score})

    # --- Only consider last 7 days ---
    today = datetime.now().date()
    last_7_days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]  # 7 days, oldest to newest

    # Filter moods and sessions to last 7 days
    moods_7d = [m for m in moods if datetime.strptime(m["date"], "%Y-%m-%d").date() in last_7_days]
    sessions_7d = []
    for s in sessions:
        # Try to get session date from 'start_time', 'timestamp', or first message
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
        if session_date and session_date in last_7_days:
            sessions_7d.append(s)

    # --- Therapy Sessions (last 7 days) ---
    therapy_sessions = len(sessions_7d)

    # --- Mood Entries (last 7 days) ---
    mood_entries = len(moods_7d)

    # --- Day Streak: always 7 for last 7 days ---
    streak = 7

    # --- Total Time (sum of session durations, in hours, last 7 days) ---
    total_minutes = 0
    for s in sessions_7d:
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
            
            # Fallback to other duration calculation methods
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

    return jsonify({
        "therapy_sessions": therapy_sessions,
        "mood_entries": mood_entries,
        "day_streak": streak,
        "total_time": f"{total_hours}h"
    })

def get_firestore_client():
    return firestore.client()

# Helper: get week range (Mon-Sun)
def get_week_range():
    today = datetime.utcnow()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end

# Helper: fetch sessions for user

# Helper: fetch sessions for user by matching document IDs (user_id_bot_name)
def get_user_sessions(uid):
    db = get_firestore_client()
    sessions_ref = db.collection('sessions').stream()
    sessions = []
    for doc in sessions_ref:
        doc_id = doc.id
        if doc_id.startswith(uid + "_"):
            session = doc.to_dict()
            session['__doc_id'] = doc_id  # keep for bot_name extraction
            sessions.append(session)
    return sessions

# Helper: store analytics
def store_analytics(uid, analytics):
    db = get_firestore_client()
    db.collection('analytics').document(uid).set(analytics, merge=True)







@progress_bp.route('/session_heatmap', methods=['GET'])
def session_heatmap():
    """Return a heatmap of session counts by day of week and time slot (6AM, 9AM, 12PM, 3PM, 6PM, 9PM), starting from the user's first session day"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        sessions = get_user_sessions(user_id)
        # Define slots
        slots = [(6,9,'6AM'), (9,12,'9AM'), (12,15,'12PM'), (15,18,'3PM'), (18,21,'6PM'), (21,24,'9PM')]
        # Find the first session's day
        first_dt = None
        for session in sessions:
            if 'timestamp' in session:
                first_dt = parse_ts(session['timestamp'])
                break
            elif 'messages' in session and session['messages'] and 'timestamp' in session['messages'][0]:
                first_dt = parse_ts(session['messages'][0]['timestamp'])
                break
        if first_dt:
            # Build week_days starting from first session's day
            all_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            start_idx = all_days.index(first_dt.strftime('%a'))
            week_days = all_days[start_idx:] + all_days[:start_idx]
        else:
            week_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        # Initialize heatmap
        heatmap = {day: {slot[2]: 0 for slot in slots} for day in week_days}
        # Fill heatmap
        for session in sessions:
            # Get timestamp from session or first message
            if 'timestamp' in session:
                dt = parse_ts(session['timestamp'])
            elif 'messages' in session and session['messages'] and 'timestamp' in session['messages'][0]:
                dt = parse_ts(session['messages'][0]['timestamp'])
            else:
                continue
            day = dt.strftime('%a')
            hour = dt.hour
            for start, end, label in slots:
                if start <= hour < end:
                    if day in heatmap:
                        heatmap[day][label] += 1
                    break
        # Return as list of dicts for easy frontend rendering
        heatmap_list = []
        for day in week_days:
            row = {'day': day}
            row.update(heatmap[day])
            heatmap_list.append(row)
        # --- Usage Insights (generated from heatmap) ---
        slot_labels = ['6AM','9AM','12PM','3PM','6PM','9PM']
        # 1. Most active: Find the slot and day with the highest count
        max_count = 0
        most_active_day = None
        most_active_slot = None
        for row in heatmap_list:
            for label in slot_labels:
                if row[label] > max_count:
                    max_count = row[label]
                    most_active_day = row['day']
                    most_active_slot = label
        # 2. Crisis support peaks: Monday mornings (Mon 6AM/9AM high)
        mon_morning_count = 0
        for row in heatmap_list:
            if row['day'] == 'Mon':
                mon_morning_count = row['6AM'] + row['9AM']
                break
        # 3. Journaling preferred: Evening hours (6PM/9PM most active overall)
        slot_totals = {label: 0 for label in slot_labels}
        for row in heatmap_list:
            for label in slot_labels:
                slot_totals[label] += row[label]
        evening_total = slot_totals['6PM'] + slot_totals['9PM']
        morning_total = slot_totals['6AM'] + slot_totals['9AM']
        # 4. Breathing exercises: High stress periods (3PM/6PM > 12PM)
        breathing_total = slot_totals['3PM'] + slot_totals['6PM']
        noon_total = slot_totals['12PM']

        usage_insights = []
        if most_active_day and most_active_slot:
            usage_insights.append(f"Most active period: {most_active_slot} on {most_active_day} (sessions: {max_count})")
        if mon_morning_count > 0:
            usage_insights.append(f"Crisis support peak detected: {mon_morning_count} sessions on Monday morning (6AM/9AM)")
        if evening_total > morning_total:
            usage_insights.append(f"Journaling is preferred in the evening (6PM/9PM): {evening_total} vs morning (6AM/9AM): {morning_total}")
        if breathing_total > noon_total:
            usage_insights.append(f"Breathing exercises likely during high stress (3PM/6PM): {breathing_total} vs noon (12PM): {noon_total}")

        return jsonify({'heatmap': heatmap_list, 'usage_insights': usage_insights})
    except Exception as e:
        return jsonify({'error': f'Failed to generate session heatmap: {str(e)}'}), 500

@progress_bp.route('/session_bar_chart', methods=['GET'])
def session_bar_chart():
    """Return session frequency per weekday for bar chart analytics and session insights"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        sessions = get_user_sessions(user_id)
        # Count sessions per weekday
        week_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        freq = {d: 0 for d in week_days}
        for session in sessions:
            # Get timestamp from session or first message
            if 'timestamp' in session:
                dt = parse_ts(session['timestamp'])
            elif 'messages' in session and session['messages'] and 'timestamp' in session['messages'][0]:
                dt = parse_ts(session['messages'][0]['timestamp'])
            else:
                continue
            day = dt.strftime('%a')
            if day in freq:
                freq[day] += 1
        # Return as list for frontend
        bar_data = [{'day': d, 'count': freq[d]} for d in week_days]

        # --- Session Insights ---
        # Peak engagement
        max_day = max(freq, key=freq.get)
        # Find peak slot (evening)
        evening_sessions = [s for s in sessions if 'timestamp' in s and 18 <= parse_ts(s['timestamp']).hour < 21]
        peak_evening_day = None
        if evening_sessions:
            peak_evening_day = max(set([parse_ts(s['timestamp']).strftime('%a') for s in evening_sessions]), key=[parse_ts(s['timestamp']).strftime('%a') for s in evening_sessions].count)
        # Average session duration
        durations = []
        for s in sessions:
            # Check for duration in dailyLogs first
            if 'dailyLogs' in s:
                for date_key, log_data in s['dailyLogs'].items():
                    if isinstance(log_data, dict) and 'duration' in log_data:
                        duration = log_data['duration']
                        if duration and duration > 0:
                            durations.append(duration)
            # Fallback to direct duration field
            elif s.get('duration', 0) > 0:
                durations.append(s.get('duration', 0))
        
        if durations:
            avg_duration = round(sum(durations) / len(durations))
            avg_duration_str = f"{avg_duration} minutes"
        else:
            avg_duration_str = "--"
        # Most effective (by bot or type if available)
        effective = None
        for s in sessions:
            if s.get('bot_name') and 'CBT' in s.get('bot_name'):
                effective = 'CBT-focused sessions'
                break
        if not effective:
            effective = 'Most attended session type'
        # Completion rate
        completion_rate = round(sum([1 for s in sessions if s.get('completed', True)]) / max(len(sessions), 1) * 100, 1)
        session_insights = [
            f"Peak engagement: {max_day}{' evenings' if peak_evening_day == max_day else ''}",
            f"Average session duration: {avg_duration_str}",
            f"Most effective: {effective}",
            f"Completion rate: {completion_rate}%"
        ]
        return jsonify({'bar_chart': bar_data, 'session_insights': session_insights})
    except Exception as e:
        return jsonify({'error': f'Failed to generate session bar chart: {str(e)}'}), 500

def parse_ts(ts):
    if isinstance(ts, datetime):
        return ts
    try:
        return datetime.fromisoformat(ts)
    except:
        return datetime.utcfromtimestamp(float(ts))

def calc_streak(sessions):
    days = set()
    for s in sessions:
        if 'timestamp' in s:
            dt = parse_ts(s['timestamp'])
            days.add(dt.date())
    streak = 0
    today = datetime.utcnow().date()
    while today in days:
        streak += 1
        today -= timedelta(days=1)
    return streak


# New: Fetch mood scores from deepseek insights stored in analytics collection
def calculate_mood_scores(user_id):
    db = get_firestore_client()
    doc = db.collection('analytics').document(user_id).get()
    if not doc.exists:
        return {}
    data = doc.to_dict()
    insights = data.get('deepseek_insights', None)
    if not insights:
        return {}
    # Try to extract mood scores from insights (assume insights is a dict with 'mood_scores' or similar)
    # If insights is a string, try to parse for mood scores (customize as needed)
    if isinstance(insights, dict) and 'mood_scores' in insights:
        return insights['mood_scores']
    # If insights is a string, try to parse lines like: 'Mood on 2025-07-09: 7'
    import re
    mood_scores = {}
    for line in str(insights).split('\n'):
        m = re.match(r"Mood on (\d{4}-\d{2}-\d{2}): (\d+)", line)
        if m:
            date, score = m.group(1), int(m.group(2))
            mood_scores[date] = score
    return mood_scores

@progress_bp.route('/mood_scores', methods=['GET'])
def get_mood_scores():
    """Get mood scores for days with sessions only, using deepseek insights"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        # Fetch mood scores from deepseek insights
        mood_scores = calculate_mood_scores(user_id)
        daily_scores = []
        for date_str, score in sorted(mood_scores.items()):
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                daily_scores.append({
                    'date': dt.strftime('%a'),  # Day name (Mon, Tue, etc.)
                    'date_full': date_str,
                    'score': score,
                    'category': 'Good' if score >= 7 else 'Okay' if score >= 4 else 'Difficult'
                })
            except Exception:
                continue
        return jsonify({'mood_scores': daily_scores})
    except Exception as e:
        return jsonify({'error': f'Failed to generate mood scores: {str(e)}'}), 500
# --- Mood Trend Analysis Endpoint ---
@progress_bp.route('/mood_trend_analysis', methods=['GET'])
def mood_trend_analysis():
    """
    Returns 7-day mood trend analysis for the user, using real mood scores from analytics.
    Output: list of days (Mon-Sun), mood score, and category (Good/Okay/Difficult)
    Query params: user_id (required)
    """
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Fetch mood scores from analytics (deepseek_insights)
    mood_scores = calculate_mood_scores(user_id)
    today = datetime.now().date()
    last_7_days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]  # 7 days, oldest to newest

    # Build trend data for each day (Mon-Sun order, always 7 days)
    trend = []
    for day in last_7_days:
        date_str = day.strftime('%Y-%m-%d')
        score = mood_scores.get(date_str)
        if score is not None:
            category = 'Good' if score >= 7 else 'Okay' if score >= 4 else 'Difficult'
        else:
            category = ""  # Use empty string instead of null
            score = ""     # Use empty string instead of null
        trend.append({
            'date': day.strftime('%a'),
            'date_full': date_str,
            'score': score,
            'category': category
        })

    return jsonify({'mood_trend': trend})

async def call_function_async(func, *args, **kwargs):
    """Helper to run synchronous functions in async context"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)

async def clinical_overview_async(user_id):
    """Async version of clinical overview"""
    # Get the synchronous function result
    from flask import Flask
    app = Flask(__name__)
    with app.test_request_context(f'/clinical_overview?user_id={user_id}'):
        result = clinical_overview()
        return result.get_json()

async def mood_trend_analysis_async(user_id):
    """Async version of mood trend analysis"""
    from flask import Flask
    app = Flask(__name__)
    with app.test_request_context(f'/mood_trend_analysis?user_id={user_id}'):
        result = mood_trend_analysis()
        return result.get_json()

async def session_bar_chart_async(user_id):
    """Async version of session bar chart"""
    from flask import Flask
    app = Flask(__name__)
    with app.test_request_context(f'/session_bar_chart?user_id={user_id}'):
        result = session_bar_chart()
        return result.get_json()

async def session_heatmap_async(user_id):
    """Async version of session heatmap"""
    from flask import Flask
    app = Flask(__name__)
    with app.test_request_context(f'/session_heatmap?user_id={user_id}'):
        result = session_heatmap()
        return result.get_json()
