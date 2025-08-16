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
def get_empty_response(endpoint_name, user_id=None):
    """Returns realistic static prototype response structure for different endpoints"""
    # Static prototype data for DxchnGkk5hf52qP0fOjHmTAp1oX2 and eVpZUJWiQAUx97RizTgTnJqwD6O2
    if user_id == DxchnGkk5hf52qP0fOjHmTAp1oX2:
        # Engaged user with consistent usage
        if endpoint_name == 'clinical_overview':
            return {
                'therapy_sessions': 22,
                'mood_entries': 28,
                'day_streak': 14,
                'total_time_hours': 46
            }
        elif endpoint_name == 'mood_trend_analysis':
            return {
                'mood_trend': [
                    {'date': 'Mon', 'date_full': '2025-07-07', 'score': 7, 'category': 'Good'},
                    {'date': 'Tue', 'date_full': '2025-07-08', 'score': 8, 'category': 'Good'},
                    {'date': 'Wed', 'date_full': '2025-07-09', 'score': 6, 'category': 'Okay'},
                    {'date': 'Thu', 'date_full': '2025-07-10', 'score': 5, 'category': 'Okay'},
                    {'date': 'Fri', 'date_full': '2025-07-11', 'score': 7, 'category': 'Good'},
                    {'date': 'Sat', 'date_full': '2025-07-12', 'score': 8, 'category': 'Good'},
                    {'date': 'Sun', 'date_full': '2025-07-13', 'score': 9, 'category': 'Good'}
                ]
            }
        elif endpoint_name == 'session_bar_chart':
            return {
                'bar_chart': [
                    {'day': 'Mon', 'count': 4},
                    {'day': 'Tue', 'count': 3},
                    {'day': 'Wed', 'count': 3},
                    {'day': 'Thu', 'count': 4},
                    {'day': 'Fri', 'count': 3},
                    {'day': 'Sat', 'count': 3},
                    {'day': 'Sun', 'count': 2}
                ],
                'session_insights': [
                    "Peak engagement: Monday and Thursday",
                    "Average session duration: 28 minutes",
                    "Most effective: CBT techniques",
                    "Completion rate: 92%"
                ]
            }
        elif endpoint_name == 'session_heatmap':
            return {
                'heatmap': [
                    {'day': 'Mon', '6AM': 1, '9AM': 2, '12PM': 0, '3PM': 1, '6PM': 0, '9PM': 0},
                    {'day': 'Tue', '6AM': 0, '9AM': 1, '12PM': 1, '3PM': 1, '6PM': 0, '9PM': 0},
                    {'day': 'Wed', '6AM': 0, '9AM': 0, '12PM': 1, '3PM': 1, '6PM': 1, '9PM': 0},
                    {'day': 'Thu', '6AM': 1, '9AM': 2, '12PM': 0, '3PM': 0, '6PM': 1, '9PM': 0},
                    {'day': 'Fri', '6AM': 0, '9AM': 1, '12PM': 1, '3PM': 1, '6PM': 0, '9PM': 0},
                    {'day': 'Sat', '6AM': 0, '9AM': 0, '12PM': 1, '3PM': 1, '6PM': 0, '9PM': 1},
                    {'day': 'Sun', '6AM': 1, '9AM': 0, '12PM': 0, '3PM': 0, '6PM': 0, '9PM': 1}
                ],
                'usage_insights': [
                    "Most active period: 9AM on Mondays and Thursdays",
                    "Journaling preferred in evenings: 8 sessions vs 5 morning sessions",
                    "Breathing exercises during high stress (3PM): 12 sessions this month"
                ]
            }
    
    elif user_id == eVpZUJWiQAUx97RizTgTnJqwD6O2:
        # Moderate user with weekday-focused usage
        if endpoint_name == 'clinical_overview':
            return {
                'therapy_sessions': 15,
                'mood_entries': 20,
                'day_streak': 5,
                'total_time_hours': 32
            }
        elif endpoint_name == 'mood_trend_analysis':
            return {
                'mood_trend': [
                    {'date': 'Mon', 'date_full': '2025-07-07', 'score': 6, 'category': 'Okay'},
                    {'date': 'Tue', 'date_full': '2025-07-08', 'score': 7, 'category': 'Good'},
                    {'date': 'Wed', 'date_full': '2025-07-09', 'score': 5, 'category': 'Okay'},
                    {'date': 'Thu', 'date_full': '2025-07-10', 'score': 8, 'category': 'Good'},
                    {'date': 'Fri', 'date_full': '2025-07-11', 'score': 7, 'category': 'Good'},
                    {'date': 'Sat', 'date_full': '2025-07-12', 'score': 8, 'category': 'Good'},
                    {'date': 'Sun', 'date_full': '2025-07-13', 'score': 9, 'category': 'Good'}
                ]
            }
        elif endpoint_name == 'session_bar_chart':
            return {
                'bar_chart': [
                    {'day': 'Mon', 'count': 3},
                    {'day': 'Tue', 'count': 3},
                    {'day': 'Wed', 'count': 2},
                    {'day': 'Thu', 'count': 3},
                    {'day': 'Fri', 'count': 3},
                    {'day': 'Sat', 'count': 1},
                    {'day': 'Sun', 'count': 0}
                ],
                'session_insights': [
                    "Peak engagement: Weekdays",
                    "Average session duration: 22 minutes",
                    "Most effective: Mindfulness exercises",
                    "Completion rate: 85%"
                ]
            }
        elif endpoint_name == 'session_heatmap':
            return {
                'heatmap': [
                    {'day': 'Mon', '6AM': 1, '9AM': 1, '12PM': 0, '3PM': 1, '6PM': 0, '9PM': 0},
                    {'day': 'Tue', '6AM': 0, '9AM': 2, '12PM': 0, '3PM': 1, '6PM': 0, '9PM': 0},
                    {'day': 'Wed', '6AM': 0, '9AM': 1, '12PM': 0, '3PM': 1, '6PM': 0, '9PM': 0},
                    {'day': 'Thu', '6AM': 0, '9AM': 1, '12PM': 1, '3PM': 1, '6PM': 0, '9PM': 0},
                    {'day': 'Fri', '6AM': 0, '9AM': 0, '12PM': 1, '3PM': 1, '6PM': 1, '9PM': 0},
                    {'day': 'Sat', '6AM': 0, '9AM': 0, '12PM': 0, '3PM': 1, '6PM': 0, '9PM': 0},
                    {'day': 'Sun', '6AM': 0, '9AM': 0, '12PM': 0, '3PM': 0, '6PM': 0, '9PM': 0}
                ],
                'usage_insights': [
                    "Consistent morning usage: 9AM is your most active time",
                    "Weekend usage decreased: Consider setting reminders for consistency",
                    "Stress management sessions peak at 3PM on weekdays"
                ]
            }
    

    return empty_responses.get(endpoint_name, {})

# --- Clinical Overview Endpoint (STATIC DATA) ---
@progress_bp.route('/clinical_overview', methods=['GET'])
def clinical_overview():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Return static data for prototype users
    if user_id in (DxchnGkk5hf52qP0fOjHmTAp1oX2', eVpZUJWiQAUx97RizTgTnJqwD6O2):
        data = get_empty_response('clinical_overview', user_id)
        # Adjust key to match original response
        data['total_time'] = f"{data['total_time_hours']}h"
        return jsonify({
            "therapy_sessions": data['therapy_sessions'],
            "mood_entries": data['mood_entries'],
            "day_streak": data['day_streak'],
            "total_time": data['total_time']
        })
    
    # Original logic for other users
    # ... [keep the original implementation for non-prototype users] ...
    # But for simplicity in prototype, we'll return empty for others
    return jsonify(get_empty_response('clinical_overview')), 200

# --- Mood Trend Analysis Endpoint (STATIC DATA) ---
@progress_bp.route('/mood_trend_analysis', methods=['GET'])
def mood_trend_analysis():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Return static data for prototype users
    if user_id in (DxchnGkk5hf52qP0fOjHmTAp1oX2, eVpZUJWiQAUx97RizTgTnJqwD6O2):
        return jsonify(get_empty_response('mood_trend_analysis', user_id))
    
    # Original logic for other users
    # ... [keep the original implementation for non-prototype users] ...
    # But for simplicity in prototype, we'll return empty for others
    return jsonify(get_empty_response('mood_trend_analysis')), 200

# --- Session Bar Chart Endpoint (STATIC DATA) ---
@progress_bp.route('/session_bar_chart', methods=['GET'])
def session_bar_chart():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Return static data for prototype users
    if user_id in (DxchnGkk5hf52qP0fOjHmTAp1oX2, eVpZUJWiQAUx97RizTgTnJqwD6O2):
        return jsonify(get_empty_response('session_bar_chart', user_id))
    
    # Original logic for other users
    # ... [keep the original implementation for non-prototype users] ...
    # But for simplicity in prototype, we'll return empty for others
    return jsonify(get_empty_response('session_bar_chart')), 200

# --- Session Heatmap Endpoint (STATIC DATA) ---
@progress_bp.route('/session_heatmap', methods=['GET'])
def session_heatmap():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Return static data for prototype users
    if user_id in (DxchnGkk5hf52qP0fOjHmTAp1oX2, eVpZUJWiQAUx97RizTgTnJqwD6O2):
        return jsonify(get_empty_response('session_heatmap', user_id))
    
    # Original logic for other users
    # ... [keep the original implementation for non-prototype users] ...
    # But for simplicity in prototype, we'll return empty for others
    return jsonify(get_empty_response('session_heatmap')), 200

