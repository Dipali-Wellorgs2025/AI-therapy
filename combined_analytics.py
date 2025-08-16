from flask import Flask, Blueprint, request, jsonify

# app = Flask(__name__)
combined_bp = Blueprint('combined', __name__)

# --- Static 2-month analytics for 2 users ---
USER_ANALYTICS = {
    "DxchnGkk5hf52qP0fOjHmTAp1oX2": {   # user1
        "clinical_overview": {
            "day_streak": 28,
            "mood_entries": 45,
            "therapy_sessions": 32,
            "total_time": "64h"
        },
        "mood_trend_analysis": [
            {"category": "good", "date": "Mon", "date_full": "2025-06-16", "score": 7},
            {"category": "okay", "date": "Tue", "date_full": "2025-06-17", "score": 5},
            {"category": "Difficult", "date": "Wed", "date_full": "2025-06-18", "score": 3},
            {"category": "okay", "date": "Thu", "date_full": "2025-06-19", "score": 4},
            {"category": "good", "date": "Fri", "date_full": "2025-06-20", "score": 8},
            {"category": "okay", "date": "Sat", "date_full": "2025-06-21", "score": 6},
            {"category": "good", "date": "Sun", "date_full": "2025-06-22", "score": 7}
            # … continue for 2 months …
        ],
        "session_bar_chart": [
            {"day": "Mon", "count": 6},
            {"day": "Tue", "count": 5},
            {"day": "Wed", "count": 4},
            {"day": "Thu", "count": 7},
            {"day": "Fri", "count": 6},
            {"day": "Sat", "count": 2},
            {"day": "Sun", "count": 2}
        ],
        "session_heatmap": [
            {"day": "Mon", "6AM": 0, "9AM": 2, "12PM": 1, "3PM": 1, "6PM": 2, "9PM": 0},
            {"day": "Tue", "6AM": 0, "9AM": 1, "12PM": 2, "3PM": 1, "6PM": 1, "9PM": 0},
            {"day": "Wed", "6AM": 0, "9AM": 1, "12PM": 1, "3PM": 0, "6PM": 2, "9PM": 1},
            {"day": "Thu", "6AM": 0, "9AM": 2, "12PM": 2, "3PM": 1, "6PM": 2, "9PM": 0},
            {"day": "Fri", "6AM": 0, "9AM": 0, "12PM": 1, "3PM": 1, "6PM": 3, "9PM": 1},
            {"day": "Sat", "6AM": 0, "9AM": 0, "12PM": 0, "3PM": 1, "6PM": 1, "9PM": 0},
            {"day": "Sun", "6AM": 0, "9AM": 0, "12PM": 1, "3PM": 0, "6PM": 1, "9PM": 0}
        ],
        "session_insights": [
            "Peak engagement: Thu evenings",
            "Average session duration: 1h 15m",
            "Most effective bot: Sage",
            "Completion rate: 82%"
        ],
        "usage_insights": [
            "Prefers weekday evenings",
            "More consistent in July than June",
            "Shows preference for anxiety and breakup support bots"
        ],
        "model_effectiveness": [
            {"bot_name": "Ava", "avg_rating": 4.5, "effectiveness": "88%", "session_count": 6},
            {"bot_name": "Jordan", "avg_rating": 4.0, "effectiveness": "80%", "session_count": 8},
            {"bot_name": "Phoenix", "avg_rating": 3.5, "effectiveness": "70%", "session_count": 5},
            {"bot_name": "Raya", "avg_rating": 4.2, "effectiveness": "84%", "session_count": 4},
            {"bot_name": "River", "avg_rating": 3.8, "effectiveness": "76%", "session_count": 3},
            {"bot_name": "Sage", "avg_rating": 4.7, "effectiveness": "90%", "session_count": 6}
        ],
        "clinical_insights_and_recommendations": {
            "progress_indicators": [
                "Consistent 2-week wellness streak",
                "Increased willingness to discuss family dynamics",
                "Engaged in grounding exercises 10+ times"
            ],
            "progress_insights": [
                {"title": "Anxiety management", "subtitle": "Practicing breathing with Sage"},
                {"title": "Conflict resolution", "subtitle": "Dialogues with Ava improved boundary setting"}
            ],
            "risk_assessment": [
                "Mild anxiety spikes during stressful work weeks",
                "Occasional avoidance behaviors observed"
            ],
            "therapeutic_effectiveness": [
                "Grounding techniques moderately effective",
                "Peer support bot sessions improved self-worth"
            ],
            "treatment_recommendations": [
                "Introduce CBT worksheets for anxiety",
                "Encourage journaling on family interactions",
                "Weekly check-ins to track resilience progress"
            ]
        },
        "summary": "User1 has shown consistent engagement across two months, with visible improvements in anxiety management and self-awareness. Still requires structured CBT intervention for sustained resilience."
    },

    "eVpZUJWiQAUx97RizTgTnJqwD6O2": {   # user2
        "clinical_overview": {
            "day_streak": 6,
            "mood_entries": 15,
            "therapy_sessions": 10,
            "total_time": "12h"
        },
        "mood_trend_analysis": [
            {"category": "okay", "date": "Mon", "date_full": "2025-06-16", "score": 5},
            {"category": "Difficult", "date": "Tue", "date_full": "2025-06-17", "score": 3},
            {"category": "good", "date": "Wed", "date_full": "2025-06-18", "score": 7},
            {"category": "okay", "date": "Thu", "date_full": "2025-06-19", "score": 4},
            {"category": "okay", "date": "Fri", "date_full": "2025-06-20", "score": 5},
            {"category": "Difficult", "date": "Sat", "date_full": "2025-06-21", "score": 2},
            {"category": "good", "date": "Sun", "date_full": "2025-06-22", "score": 8}
            # … continue for 2 months …
        ],
        "session_bar_chart": [
            {"day": "Mon", "count": 2},
            {"day": "Tue", "count": 1},
            {"day": "Wed", "count": 2},
            {"day": "Thu", "count": 2},
            {"day": "Fri", "count": 1},
            {"day": "Sat", "count": 1},
            {"day": "Sun", "count": 1}
        ],
        "session_heatmap": [
            {"day": "Mon", "6AM": 0, "9AM": 0, "12PM": 1, "3PM": 1, "6PM": 0, "9PM": 0},
            {"day": "Tue", "6AM": 0, "9AM": 0, "12PM": 0, "3PM": 1, "6PM": 0, "9PM": 0},
            {"day": "Wed", "6AM": 0, "9AM": 0, "12PM": 1, "3PM": 0, "6PM": 1, "9PM": 0},
            {"day": "Thu", "6AM": 0, "9AM": 1, "12PM": 0, "3PM": 1, "6PM": 0, "9PM": 0},
            {"day": "Fri", "6AM": 0, "9AM": 0, "12PM": 0, "3PM": 0, "6PM": 1, "9PM": 0},
            {"day": "Sat", "6AM": 0, "9AM": 0, "12PM": 1, "3PM": 0, "6PM": 0, "9PM": 0},
            {"day": "Sun", "6AM": 0, "9AM": 0, "12PM": 0, "3PM": 1, "6PM": 0, "9PM": 0}
        ],
        "session_insights": [
            "Peak engagement: Wed afternoons",
            "Average session duration: 45m",
            "Most effective bot: Jordan",
            "Completion rate: 60%"
        ],
        "usage_insights": [
            "Engages mostly mid-week",
            "Skips weekends frequently",
            "Shows preference for breakup and trauma support bots"
        ],
        "model_effectiveness": [
            {"bot_name": "Ava", "avg_rating": 3.8, "effectiveness": "70%", "session_count": 2},
            {"bot_name": "Jordan", "avg_rating": 4.2, "effectiveness": "82%", "session_count": 4},
            {"bot_name": "Phoenix", "avg_rating": 3.5, "effectiveness": "72%", "session_count": 3},
            {"bot_name": "Sage", "avg_rating": 3.0, "effectiveness": "60%", "session_count": 1}
        ],
        "clinical_insights_and_recommendations": {
            "progress_indicators": [
                "Attended 3 consecutive weekday sessions",
                "Opened up about breakup-related stress"
            ],
            "progress_insights": [
                {"title": "Resilience", "subtitle": "Returned after skipped week"},
                {"title": "Trauma support", "subtitle": "Expressed need for Phoenix in flashback moments"}
            ],
            "risk_assessment": [
                "Inconsistent engagement may hinder recovery",
                "Breakup stress still unresolved"
            ],
            "therapeutic_effectiveness": [
                "Jordan effective in emotional stabilization",
                "Phoenix partially effective in trauma reprocessing"
            ],
            "treatment_recommendations": [
                "Encourage daily mood check-ins",
                "Suggest regular grounding exercises",
                "Introduce guided meditations"
            ]
        },
        "summary": "User2 engages sporadically with preference for breakup and trauma support bots. Shows resilience but needs consistency and daily mood logging."
    }
}

@combined_bp.route('/combined_analytics', methods=['GET'])
def combined_analytics():
    user_id = request.args.get("user_id", "").strip()
    if user_id in USER_ANALYTICS:
        return jsonify(USER_ANALYTICS[user_id])
    return jsonify({"error": "User not found"}), 404




