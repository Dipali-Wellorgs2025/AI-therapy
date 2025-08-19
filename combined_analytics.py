from flask import Flask, Blueprint, request, jsonify

# app = Flask(__name__)
combined_bp = Blueprint('combined', __name__)

USER_ANALYTICS = {
    "DxchnGkk5hf52qP0fOjHmTAp1oX2": {   # user1
        "clinical_overview": {
            "day_streak": 28,
            "mood_entries": 60,
            "therapy_sessions": 48,
            "total_time": "96h"
        },
        "mood_trend_analysis": [
            {"category": "good", "date": "Mon", "date_full": "2025-06-16", "score": 7},
            {"category": "okay", "date": "Tue", "date_full": "2025-06-17", "score": 5},
            {"category": "difficult", "date": "Wed", "date_full": "2025-06-18", "score": 3},
            {"category": "okay", "date": "Thu", "date_full": "2025-06-19", "score": 4},
            {"category": "good", "date": "Fri", "date_full": "2025-06-20", "score": 8},
            {"category": "okay", "date": "Sat", "date_full": "2025-06-21", "score": 6},
            {"category": "good", "date": "Sun", "date_full": "2025-06-22", "score": 7}
            # … continue daily for 2 months …
        ],
        "session_bar_chart": [
            {"day": "Mon", "count": 7},
            {"day": "Tue", "count": 6},
            {"day": "Wed", "count": 5},
            {"day": "Thu", "count": 8},
            {"day": "Fri", "count": 7},
            {"day": "Sat", "count": 3},
            {"day": "Sun", "count": 2}
        ],
        "session_heatmap": [
            {"day": "Mon", "6AM": 1, "9AM": 3, "12PM": 2, "3PM": 1, "6PM": 3, "9PM": 1},
            {"day": "Tue", "6AM": 0, "9AM": 2, "12PM": 3, "3PM": 1, "6PM": 2, "9PM": 1},
            {"day": "Wed", "6AM": 1, "9AM": 1, "12PM": 2, "3PM": 1, "6PM": 3, "9PM": 2},
            {"day": "Thu", "6AM": 1, "9AM": 3, "12PM": 3, "3PM": 2, "6PM": 3, "9PM": 1},
            {"day": "Fri", "6AM": 0, "9AM": 1, "12PM": 2, "3PM": 2, "6PM": 4, "9PM": 2},
            {"day": "Sat", "6AM": 0, "9AM": 1, "12PM": 1, "3PM": 2, "6PM": 2, "9PM": 1},
            {"day": "Sun", "6AM": 0, "9AM": 0, "12PM": 1, "3PM": 1, "6PM": 2, "9PM": 1}
        ],
        "session_insights": [
            "Peak engagement: Thu & Fri evenings",
            "Average session duration: 1h 20m",
            "Most effective bot: Sage",
            "Completion rate: 84%",
            "Engaged 5+ days per week consistently",
            "Engagement dipped slightly during holiday week",
            "Sessions longer during high-stress work deadlines",
            "Sustained improvement in consistency between June and July",
            "Re-engages quickly after missed days"
        ],
        "usage_insights": [
            "Prefers weekday evenings",
            "More consistent in July than June",
            "Regular use of anxiety + family bots",
            "Rarely engages early mornings",
            "Weekends show lighter usage compared to weekdays",
            "Peak stress reflections appear during mid-month deadlines",
            "User gradually increased session frequency after July 1st",
            "More reliance on peer-support bots during difficult days"
        ],
        "model_effectiveness": [
            {"bot_name": "Ava", "avg_rating": 4.9, "effectiveness": "88%", "session_count": 10},
            {"bot_name": "Jordan", "avg_rating": 4.7, "effectiveness": "82%", "session_count": 12},
            {"bot_name": "Phoenix", "avg_rating": 4.6, "effectiveness": "74%", "session_count": 8},
            {"bot_name": "Raya", "avg_rating": 4.8, "effectiveness": "85%", "session_count": 7},
            {"bot_name": "River", "avg_rating": 4.6, "effectiveness": "78%", "session_count": 6},
            {"bot_name": "Sage", "avg_rating": 4.9, "effectiveness": "91%", "session_count": 9}
        ],
        "clinical_insights_and_recommendations": {
            "progress_indicators": [
                "Maintained 4-week wellness streak",
                "Increased openness about work stress",
                "Practiced journaling 12 times",
                "Improved boundary-setting skills",
                "Demonstrated better emotional regulation in July",
                "Showed resilience in coping with anxiety triggers"
            ],
            "progress_insights": [
                {"title": "Anxiety management", "subtitle": "Practicing grounding with Sage weekly"},
                {"title": "Family dynamics", "subtitle": "Better handling of conflicts after Ava sessions"},
                {"title": "Resilience", "subtitle": "Faster recovery after low mood days"},
                {"title": "Peer support", "subtitle": "Engagement with River boosted self-confidence"},
                {"title": "Work-life balance", "subtitle": "Improved time management through structured sessions"}
            ],
            "risk_assessment": [
                "Mild anxiety spikes during deadlines",
                "Occasional avoidance behaviors observed",
                "Risk of burnout if workload increases",
                "Potential dependency on weekday sessions for relief"
            ],
            "therapeutic_effectiveness": [
                "Grounding techniques highly effective in July",
                "Peer support boosted self-worth",
                "Family therapy improved communication",
                "Journaling moderately effective but needs consistency"
            ],
            "treatment_recommendations": [
                "Continue CBT worksheets for anxiety",
                "Weekly journaling for emotional tracking",
                "Encourage peer-led support sessions",
                "Introduce relaxation audio guides",
                "Promote weekend engagement through lighter exercises"
            ]
        },
        "summary": "User1 shows strong consistency across 2 months with visible improvement in anxiety regulation, conflict management, and resilience. Needs ongoing CBT and structured relaxation practices."
    },

    "eVpZUJWiQAUx97RizTgTnJqwD6O2": {   # user2
        "clinical_overview": {
            "day_streak": 12,
            "mood_entries": 55,
            "therapy_sessions": 30,
            "total_time": "40h"
        },
        "mood_trend_analysis": [
            {"category": "okay", "date": "Mon", "date_full": "2025-06-16", "score": 5},
            {"category": "difficult", "date": "Tue", "date_full": "2025-06-17", "score": 3},
            {"category": "good", "date": "Wed", "date_full": "2025-06-18", "score": 7},
            {"category": "okay", "date": "Thu", "date_full": "2025-06-19", "score": 4},
            {"category": "okay", "date": "Fri", "date_full": "2025-06-20", "score": 5},
            {"category": "difficult", "date": "Sat", "date_full": "2025-06-21", "score": 2},
            {"category": "good", "date": "Sun", "date_full": "2025-06-22", "score": 8}
            # … continue daily for 2 months …
        ],
        "session_bar_chart": [
            {"day": "Mon", "count": 3},
            {"day": "Tue", "count": 2},
            {"day": "Wed", "count": 4},
            {"day": "Thu", "count": 3},
            {"day": "Fri", "count": 2},
            {"day": "Sat", "count": 1},
            {"day": "Sun", "count": 2}
        ],
        "session_heatmap": [
            {"day": "Mon", "6AM": 0, "9AM": 1, "12PM": 2, "3PM": 1, "6PM": 1, "9PM": 0},
            {"day": "Tue", "6AM": 0, "9AM": 0, "12PM": 1, "3PM": 1, "6PM": 1, "9PM": 0},
            {"day": "Wed", "6AM": 0, "9AM": 1, "12PM": 2, "3PM": 1, "6PM": 2, "9PM": 0},
            {"day": "Thu", "6AM": 0, "9AM": 1, "12PM": 1, "3PM": 1, "6PM": 1, "9PM": 0},
            {"day": "Fri", "6AM": 0, "9AM": 0, "12PM": 1, "3PM": 1, "6PM": 1, "9PM": 0},
            {"day": "Sat", "6AM": 0, "9AM": 0, "12PM": 1, "3PM": 0, "6PM": 1, "9PM": 0},
            {"day": "Sun", "6AM": 0, "9AM": 0, "12PM": 1, "3PM": 1, "6PM": 0, "9PM": 0}
        ],
        "session_insights": [
            "Peak engagement: Wed afternoons",
            "Average session duration: 50m",
            "Most effective bot: Jordan",
            "Completion rate: 68%",
            "Re-engaged after skipping weekends",
            "Sessions are shorter but more intense emotionally",
            "Tends to log in post stressful conversations with peers",
            "Shows higher engagement after difficult mood entries"
        ],
        "usage_insights": [
            "Mid-week sessions preferred",
            "Inconsistent during weekends",
            "Uses breakup + trauma bots most",
            "Improved July consistency over June",
            "More open during late evening sessions",
            "Skipped multiple sessions during exam week",
            "Uses chat as a safe space during loneliness"
        ],
        "model_effectiveness": [
            {"bot_name": "Ava", "avg_rating": 4.6, "effectiveness": "72%", "session_count": 5},
            {"bot_name": "Jordan", "avg_rating": 4.8, "effectiveness": "84%", "session_count": 10},
            {"bot_name": "Phoenix", "avg_rating": 4.7, "effectiveness": "75%", "session_count": 8},
            {"bot_name": "Sage", "avg_rating": 4.5, "effectiveness": "68%", "session_count": 4},
            {"bot_name": "Raya", "avg_rating": 4.6, "effectiveness": "73%", "session_count": 3}
        ],
        "clinical_insights_and_recommendations": {
            "progress_indicators": [
                "Logged moods for 10 consecutive days",
                "Shared about breakup stress more openly",
                "Started grounding exercises 6 times",
                "Able to identify emotional triggers",
                "Showed willingness to try new coping strategies"
            ],
            "progress_insights": [
                {"title": "Resilience", "subtitle": "Came back after skipped days"},
                {"title": "Breakup recovery", "subtitle": "Progress with Jordan sessions"},
                {"title": "Trauma processing", "subtitle": "Benefiting from Phoenix interventions"},
                {"title": "Self-reflection", "subtitle": "Expressed deeper insights about personal patterns"},
                {"title": "Support-seeking", "subtitle": "Shows readiness to rely on multiple bots"}
            ],
            "risk_assessment": [
                "Drop-off risk on weekends",
                "Breakup stress unresolved",
                "Sleep disturbances reported occasionally",
                "Potential risk of social withdrawal during low mood days"
            ],
            "therapeutic_effectiveness": [
                "Felt calmer after regular journaling practice",
                "Sleep improved slightly with consistent routine",
                "Stress levels reduced by practicing breathing exercises",
                "Confidence increased after daily affirmations",
                "Energy levels improved with better hydration",
                "Felt more focused after reducing screen time",
                "Improved social interactions by staying present in conversations",
            ],
            "treatment_recommendations": [
                "Encourage daily check-ins",
                "Suggest guided meditations before sleep",
                "Weekly review of progress with breakup stress",
                "Promote weekend consistency with light journaling",
                "Introduce resilience-focused exercises for long-term recovery"
            ]
        },
        "summary": "User2 engaged ~30 sessions in 2 months, mostly mid-week. Consistency improved in July but weekends remain weak. Shows resilience but needs structured daily tracking for long-term recovery."
    }
}

@combined_bp.route('/combined_analytics', methods=['GET'])
def combined_analytics():
    user_id = request.args.get("user_id", "").strip()
    if user_id in USER_ANALYTICS:
        return jsonify(USER_ANALYTICS[user_id])
    return jsonify({"error": "User not found"}), 404




