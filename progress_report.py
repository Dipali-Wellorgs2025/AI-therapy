from flask import Blueprint, request, jsonify
from firebase_admin import firestore
from datetime import datetime, timedelta
import calendar
import io
import base64
import asyncio
from functools import wraps
import re

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
    Query params: user_id (required), start_date (optional, YYYY-MM-DD)
    """
    user_id = request.args.get('user_id')
    start_date = request.args.get('start_date')
    
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Check weekly gating logic
    gating_result = get_week_window_and_validate(user_id, start_date)
    if not gating_result['valid']:
        return jsonify(get_empty_response('clinical_overview')), 200

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
            for line in insights.split('\n'):
                m = re.match(r"Mood on (\d{4}-\d{2}-\d{2}): (\d+)", line)
                if m:
                    date, score = m.group(1), int(m.group(2))
                    moods.append({'user_id': user_id, 'date': date, 'score': score})

    # --- Only consider the specific week's data ---
    week_start = gating_result['week_start'].date()
    week_end = gating_result['week_end'].date()
    
    print(f"Filtering data for week: {week_start} to {week_end}")
    
    # Get all dates in the target week
    week_dates = []
    current_date = week_start
    while current_date <= week_end:
        week_dates.append(current_date)
        current_date += timedelta(days=1)

    # Filter moods and sessions to the specific week
    moods_week = [m for m in moods if datetime.strptime(m["date"], "%Y-%m-%d").date() in week_dates]
    sessions_week = []
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
        if session_date and session_date in week_dates:
            sessions_week.append(s)

    # --- Therapy Sessions (specific week) ---
    therapy_sessions = len(sessions_week)

    # --- Mood Entries (specific week) ---
    mood_entries = len(moods_week)

    # --- Day Streak: calculate based on consecutive days in the week ---
    streak = 0
    for date in week_dates:
        has_session = False
        for s in sessions_week:
            # Get session date
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
            
            if session_date == date:
                has_session = True
                break
                
        if has_session:
            streak += 1
        else:
            break  # Streak broken

    # --- Total Time (sum of session durations, in hours, specific week) ---
    total_minutes = 0
    for s in sessions_week:
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
        start_date = request.args.get('start_date')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400

        # Check weekly gating logic
        gating_result = get_week_window_and_validate(user_id, start_date)
        if not gating_result['valid']:
            return jsonify(get_empty_response('session_heatmap')), 200
        
        # Get all sessions and filter to the specific week
        sessions = get_user_sessions(user_id)
        week_start = gating_result['week_start'].date()
        week_end = gating_result['week_end'].date()
        
        # Filter sessions to the specific week
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
        
        sessions = sessions_week  # Use only the week's sessions
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
        start_date = request.args.get('start_date')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400

        # Check weekly gating logic
        gating_result = get_week_window_and_validate(user_id, start_date)
        if not gating_result['valid']:
            return jsonify(get_empty_response('session_bar_chart')), 200
        
        # Get all sessions and filter to the specific week
        sessions = get_user_sessions(user_id)
        week_start = gating_result['week_start'].date()
        week_end = gating_result['week_end'].date()
        
        # Filter sessions to the specific week
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
        
        sessions = sessions_week  # Use only the week's sessions
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
    Query params: user_id (required), start_date (optional, YYYY-MM-DD)
    """
    user_id = request.args.get('user_id')
    start_date = request.args.get('start_date')
    
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Check weekly gating logic
    gating_result = get_week_window_and_validate(user_id, start_date)
    if not gating_result['valid']:
        return jsonify(get_empty_response('mood_trend_analysis')), 200

    # Fetch mood scores from analytics (deepseek_insights)
    mood_scores = calculate_mood_scores(user_id)
    
    # Use the specific week boundaries from gating result
    week_start = gating_result['week_start'].date()
    week_end = gating_result['week_end'].date()
    
    # Get all dates in the target week (7 days)
    week_dates = []
    current_date = week_start
    while current_date <= week_end:
        week_dates.append(current_date)
        current_date += timedelta(days=1)

    # Build trend data for the specific week (Mon-Sun order, always 7 days)
    trend = []
    for day in week_dates:
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

async def clinical_overview_async(user_id, start_date=None):
    """Async version of clinical overview"""
    # Get the synchronous function result
    from flask import Flask
    app = Flask(__name__)
    query_string = f'user_id={user_id}'
    if start_date:
        query_string += f'&start_date={start_date}'
    with app.test_request_context(f'/clinical_overview?{query_string}'):
        result = clinical_overview()
        return result.get_json()

async def mood_trend_analysis_async(user_id, start_date=None):
    """Async version of mood trend analysis"""
    from flask import Flask
    app = Flask(__name__)
    query_string = f'user_id={user_id}'
    if start_date:
        query_string += f'&start_date={start_date}'
    with app.test_request_context(f'/mood_trend_analysis?{query_string}'):
        result = mood_trend_analysis()
        return result.get_json()

async def session_bar_chart_async(user_id, start_date=None):
    """Async version of session bar chart"""
    from flask import Flask
    app = Flask(__name__)
    query_string = f'user_id={user_id}'
    if start_date:
        query_string += f'&start_date={start_date}'
    with app.test_request_context(f'/session_bar_chart?{query_string}'):
        result = session_bar_chart()
        return result.get_json()

async def session_heatmap_async(user_id, start_date=None):
    """Async version of session heatmap"""
    from flask import Flask
    app = Flask(__name__)
    query_string = f'user_id={user_id}'
    if start_date:
        query_string += f'&start_date={start_date}'
    with app.test_request_context(f'/session_heatmap?{query_string}'):
        result = session_heatmap()
        return result.get_json()

# Helper functions for weekly gating logic
def get_user_first_message_date(user_id):
    """
    Get the timestamp of the very first message from user's sessions by checking all sessions
    and finding the earliest message timestamp.
    Returns: datetime object of the first message or None if no messages found
    """
    db = get_firestore_client()
    
    # Get all sessions for this user by checking document IDs that start with user_id
    sessions_ref = db.collection('sessions').stream()
    sessions = []
    
    for doc in sessions_ref:
        doc_id = doc.id
        if doc_id.startswith(user_id + "_"):
            session_data = doc.to_dict()
            if session_data:
                sessions.append(session_data)
    
    if not sessions:
        print(f"No sessions found for user {user_id}")
        return None
    
    earliest_timestamp = None
    earliest_message_info = None
    
    for session in sessions:
        messages = session.get('messages', [])
        if not messages:
            continue
            
        for i, message in enumerate(messages):
            if isinstance(message, dict):
                timestamp_str = message.get('timestamp')
                if timestamp_str:
                    try:
                        # Parse the timestamp string to datetime
                        if isinstance(timestamp_str, str):
                            # Handle ISO format with timezone
                            if '+' in timestamp_str or 'Z' in timestamp_str:
                                msg_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            else:
                                msg_time = datetime.fromisoformat(timestamp_str)
                        else:
                            # Handle timestamp as number (unix timestamp)
                            msg_time = datetime.fromtimestamp(float(timestamp_str))
                        
                        # Check if this is the earliest message
                        if earliest_timestamp is None or msg_time < earliest_timestamp:
                            earliest_timestamp = msg_time
                            earliest_message_info = {
                                'session_id': session.get('__doc_id', 'unknown'),
                                'message_index': i,
                                'message': message.get('message', '')[:50] + '...',
                                'sender': message.get('sender', 'unknown')
                            }
                            
                    except Exception as e:
                        print(f"Error parsing timestamp '{timestamp_str}': {e}")
                        continue
    
    if earliest_timestamp:
        print(f"Found earliest message for user {user_id}:")
        print(f"  Date: {earliest_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Message: {earliest_message_info['message']}")
        print(f"  Sender: {earliest_message_info['sender']}")
    
    return earliest_timestamp

def get_week_window_and_validate(user_id, start_date=None):
    """
    Determines the weekly window and validates if analytics should be shown.
    
    LOGIC:
    - Find user's very first message timestamp 
    - Day 1 starts from that first message date
    - Week 1: Days 1-7 (analytics shown starting Day 8)
    - Week 2: Days 8-14 (analytics shown starting Day 15)
    - Week 3: Days 15-21 (analytics shown starting Day 22)
    - And so on...
    
    Args:
        user_id: User ID
        start_date: Optional start date string (YYYY-MM-DD). If provided, overrides auto-detection
    Returns:
        dict with:
        - 'valid': boolean, whether to show analytics
        - 'week_start': datetime of week start
        - 'week_end': datetime of week end  
        - 'current_day': which day in the sequence (1-based)
        - 'week_number': which week (1-based)
        - 'message': explanation string
    """
    
    # Get the starting reference date
    if start_date:
        try:
            reference_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            print(f"Using provided start_date: {reference_date}")
        except ValueError:
            return {
                'valid': False,
                'message': 'Invalid start_date format. Use YYYY-MM-DD',
                'week_start': None,
                'week_end': None,
                'current_day': 0,
                'week_number': 0
            }
    else:
        # Find user's first message date (this is Day 1)
        first_msg_time = get_user_first_message_date(user_id)
        if not first_msg_time:
            return {
                'valid': False,
                'message': 'No sessions found for user',
                'week_start': None,
                'week_end': None,
                'current_day': 0,
                'week_number': 0
            }
        reference_date = first_msg_time.date()
        print(f"Using user's first message date: {reference_date}")
    
    # Calculate current day since first message
    today = datetime.now().date()
    days_since_start = (today - reference_date).days + 1  # +1 because first day is day 1
    
    print(f"Today: {today}")
    print(f"Days since first message: {days_since_start}")
    
    # Determine which week we're in
    week_number = (days_since_start - 1) // 7 + 1  # Which week (1-based)
    day_in_current_week = (days_since_start - 1) % 7 + 1   # Which day in current week (1-7)
    
    # Calculate week boundaries for the current week
    week_start_day = (week_number - 1) * 7 + 1  # Day number when this week started
    week_start_date = reference_date + timedelta(days=week_start_day - 1)
    week_end_date = week_start_date + timedelta(days=6)
    
    print(f"Week {week_number}: Days {week_start_day}-{week_start_day + 6}")
    print(f"Week dates: {week_start_date} to {week_end_date}")
    print(f"Current day in week: {day_in_current_week}")
    
    # UPDATED GATING LOGIC: Show analytics for the most recent COMPLETED week
    # Week 1 (Days 1-7): No analytics yet
    # Day 8+ (Week 2 starts): Show Week 1 analytics
    # Day 15+ (Week 3 starts): Show Week 2 analytics
    # etc.
    
    if days_since_start <= 7:
        # Still in Week 1 - no analytics yet
        valid = False
        week_to_show = 1
        days_remaining = 8 - days_since_start
        unlock_date = reference_date + timedelta(days=7)
        message = f"❌ Week 1 not complete. Analytics unlock on day 8 ({unlock_date}) - {days_remaining} days remaining"
        week_start_date = reference_date
        week_end_date = reference_date + timedelta(days=6)
        
    else:
        # Day 8+ - show the most recent completed week
        valid = True
        completed_weeks = (days_since_start - 1) // 7  # How many complete weeks
        week_to_show = completed_weeks  # Show the last completed week
        
        # Calculate boundaries for the completed week to show
        week_start_date = reference_date + timedelta(days=(week_to_show - 1) * 7)
        week_end_date = week_start_date + timedelta(days=6)
        
        message = f"✅ Showing Week {week_to_show} analytics (days {(week_to_show-1)*7 + 1}-{week_to_show*7}) from {week_start_date} to {week_end_date}"
    
    print(f"Week to show: {week_to_show}")
    print(f"Week dates: {week_start_date} to {week_end_date}")
    print(f"Valid: {valid}")
    
    return {
        'valid': valid,
        'week_start': datetime.combine(week_start_date, datetime.min.time()),
        'week_end': datetime.combine(week_end_date, datetime.max.time()),
        'current_day': days_since_start,
        'week_number': week_to_show,
        'day_in_week': day_in_current_week,
        'message': message,
        'reference_date': reference_date,
        'completed_weeks': completed_weeks if days_since_start > 7 else 0
    }

def get_empty_response(endpoint_name):
    """Returns empty response structure for different endpoints when gating is active"""
    empty_responses = {
        'clinical_overview': {
            'therapy_sessions': 0,
            'mood_entries': 0,
            'day_streak': 0,
            'total_time_hours': 0
        },
        'mood_trend_analysis': {
            'mood_trend': []
        },
        'session_bar_chart': {
            'bar_chart': [],
            'session_insights': []
        },
        'session_heatmap': {
            'heatmap': [],
            'usage_insights': []
        },
        'model_effectiveness': [],
        'insights': {
            'Clinical_insights and Recommendations': {},
            'progress_indicators': [],
            'progress_insights': []
        }
    }
    return empty_responses.get(endpoint_name, {})
