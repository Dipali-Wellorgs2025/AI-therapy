import os
from openai import OpenAI
from datetime import date, datetime, timedelta
from flask import Blueprint, request, jsonify
from firebase_admin import firestore
# Import helpers from progress_api if needed
from progress_api import get_user_sessions, get_total_time, get_daily_motivational_quote

combined_progress_bp = Blueprint('combined_progress', __name__)
@combined_progress_bp.route('/progress/combined', methods=['GET'])
def get_combined_progress():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Static data for prototype users
    if user_id == DxchnGkk5hf52qP0fOjHmTAp1oX2 :
        # Engaged user with consistent usage
        return jsonify({
            "progress": {
                "wellness_streak": 14,
                "wellness_streak_text": "14 days of showing up for yourself",
                "milestone_message": "Two weeks of consistency!",
                "next_milestone": 21,
                "next_milestone_message": "Keep going! Next milestone at 21 days"
            },
            "healing_journey": {
                "times_showed_up": 22,
                "time_for_yourself": "46h",
                "day_streak": 14,
                "mood_checkins": 28
            },
            "milestones": [
                {
                    "title": "You Took the First Step",
                    "description": "Started your first therapy session",
                    "achieved": True,
                    "progress": 1,
                    "target": 1
                },
                {
                    "title": "You're Showing Up Regularly",
                    "description": "Completed 5 therapy sessions",
                    "achieved": True,
                    "progress": 5,
                    "target": 5
                },
                {
                    "title": "Committed to Growth",
                    "description": "Completed 10 therapy sessions",
                    "achieved": True,
                    "progress": 10,
                    "target": 10
                },
                {
                    "title": "Checking In With Yourself",
                    "description": "Logged your mood for 7 days",
                    "achieved": True,
                    "progress": 7,
                    "target": 7
                },
                {
                    "title": "Consistency Champion",
                    "description": "Maintained a 14-day wellness streak",
                    "achieved": True,
                    "progress": 14,
                    "target": 14
                },
                {
                    "title": "Wellness Warrior",
                    "description": "Completed 25 therapy sessions",
                    "achieved": False,
                    "progress": 22,
                    "target": 25
                },
                {
                    "quote": "Every small step is progress. Celebrate your journey!"
                }
            ]
        })
    
    elif user_id == eVpZUJWiQAUx97RizTgTnJqwD6O2:
        # Moderate user with weekday-focused usage
        return jsonify({
            "progress": {
                "wellness_streak": 5,
                "wellness_streak_text": "5 days of showing up for yourself",
                "milestone_message": "Keep going!",
                "next_milestone": 7,
                "next_milestone_message": "Keep going! Next milestone at 7 days"
            },
            "healing_journey": {
                "times_showed_up": 15,
                "time_for_yourself": "32h",
                "day_streak": 5,
                "mood_checkins": 20
            },
            "milestones": [
                {
                    "title": "You Took the First Step",
                    "description": "Started your first therapy session",
                    "achieved": True,
                    "progress": 1,
                    "target": 1
                },
                {
                    "title": "You're Showing Up Regularly",
                    "description": "Completed 5 therapy sessions",
                    "achieved": True,
                    "progress": 5,
                    "target": 5
                },
                {
                    "title": "Committed to Growth",
                    "description": "Completed 10 therapy sessions",
                    "achieved": True,
                    "progress": 10,
                    "target": 10
                },
                {
                    "title": "Checking In With Yourself",
                    "description": "Logged your mood for 7 days",
                    "achieved": True,
                    "progress": 7,
                    "target": 7
                },
                {
                    "title": "Consistency Champion",
                    "description": "Maintained a 14-day wellness streak",
                    "achieved": False,
                    "progress": 5,
                    "target": 14
                },
                {
                    "title": "Wellness Warrior",
                    "description": "Completed 25 therapy sessions",
                    "achieved": False,
                    "progress": 15,
                    "target": 25
                },
                {
                    "quote": "Progress is progress, no matter how small."
                }
            ]
        })
    
    # Default response for other users
    return jsonify({
        "progress": {
            "wellness_streak": 0,
            "wellness_streak_text": "0 days of showing up for yourself",
            "milestone_message": "Start your journey today!",
            "next_milestone": 7,
            "next_milestone_message": "Keep going! Next milestone at 7 days"
        },
        "healing_journey": {
            "times_showed_up": 0,
            "time_for_yourself": "0h",
            "day_streak": 0,
            "mood_checkins": 0
        },
        "milestones": [
            {
                "title": "You Took the First Step",
                "description": "Started your first therapy session",
                "achieved": False,
                "progress": 0,
                "target": 1
            },
            {
                "title": "You're Showing Up Regularly",
                "description": "Completed 5 therapy sessions",
                "achieved": False,
                "progress": 0,
                "target": 5
            },
            {
                "title": "Committed to Growth",
                "description": "Completed 10 therapy sessions",
                "achieved": False,
                "progress": 0,
                "target": 10
            },
            {
                "title": "Checking In With Yourself",
                "description": "Logged your mood for 7 days",
                "achieved": False,
                "progress": 0,
                "target": 7
            },
            {
                "title": "Consistency Champion",
                "description": "Maintained a 30-day wellness streak",
                "achieved": False,
                "progress": 0,
                "target": 30
            },
            {
                "title": "Wellness Warrior",
                "description": "Completed 25 therapy sessions",
                "achieved": False,
                "progress": 0,
                "target": 25,
            },
            {
                "quote": "Your mental health journey starts with a single step."
            }
        ]
    })
