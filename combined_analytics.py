from flask import Blueprint, request, jsonify
from progress_report import clinical_overview, get_user_sessions, get_firestore_client
from model_effectiveness import model_effectiveness
from deepseek_insights import generate_insights

combined_bp = Blueprint('combined', __name__)

@combined_bp.route('/combined_analytics', methods=['GET'])
def combined_analytics():
    """
    Returns all analytics in one API:
    - clinical_overview
    - mood_trend_analysis  
    - session_bar_chart
    - session_heatmap
    - model_effectiveness
    - clinical_insights_and_recommendations (includes progress_indicators and progress_insights)
    Query params: user_id (required), bot_id (optional)
    """
    user_id = request.args.get('user_id')
    bot_id = request.args.get('bot_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Helper to extract JSON from a Flask Response or return as-is if already dict
    def extract_json(resp):
        if hasattr(resp, 'get_json'):
            return resp.get_json()
        elif isinstance(resp, dict):
            return resp
        else:
            return {}

    # Clinical Overview
    clinical = extract_json(clinical_overview())

    # Mood Trend Analysis
    from progress_report import mood_trend_analysis, session_bar_chart, session_heatmap
    mood_trend = extract_json(mood_trend_analysis())

    # Session Bar Chart
    session_bar = extract_json(session_bar_chart())

    # Session Heatmap
    session_heat = extract_json(session_heatmap())

    # Model Effectiveness
    model_eff = extract_json(model_effectiveness())

    # Get Insights (now returns flattened structure)
    from deepseek_insights import get_insights
    get_insights_resp = extract_json(get_insights())

    # Flatten nested keys for model_effectiveness and session_bar_chart
    model_effectiveness_data = model_eff.get('model_effectiveness') if isinstance(model_eff, dict) and 'model_effectiveness' in model_eff else model_eff
    session_bar_chart_data = session_bar.get('bar_chart') if isinstance(session_bar, dict) and 'bar_chart' in session_bar else session_bar
    session_insights_data = session_bar.get('session_insights') if isinstance(session_bar, dict) and 'session_insights' in session_bar else None

    # Flatten session_heatmap
    session_heatmap_data = session_heat.get('heatmap') if isinstance(session_heat, dict) and 'heatmap' in session_heat else session_heat
    usage_insights_data = session_heat.get('usage_insights') if isinstance(session_heat, dict) and 'usage_insights' in session_heat else None

    # Flatten mood_trend_analysis
    mood_trend_data = mood_trend.get('mood_trend') if isinstance(mood_trend, dict) and 'mood_trend' in mood_trend else mood_trend

    # Extract insights data properly (no more nested 'insights' key)
    clinical_insights = get_insights_resp.get('Clinical_insights and Recommendations', {})
    progress_indicators = get_insights_resp.get('progress_indicators', [])
    progress_insights = get_insights_resp.get('progress_insights', [])

    # Add progress_indicators and progress_insights to clinical_insights_and_recommendations
    if isinstance(clinical_insights, dict):
        clinical_insights['progress_indicators'] = progress_indicators
        clinical_insights['progress_insights'] = progress_insights

    # Compose the response in the required flat structure
    response = {
        'clinical_overview': clinical,
        'mood_trend_analysis': mood_trend_data,
        'session_bar_chart': session_bar_chart_data,
        'session_insights': session_insights_data,
        'session_heatmap': session_heatmap_data,
        'usage_insights': usage_insights_data,
        'model_effectiveness': model_effectiveness_data,
        'clinical_insights_and_recommendations': clinical_insights
    }
    
    # Remove any None values to keep response clean
    response = {k: v for k, v in response.items() if v is not None}
    
    return jsonify(response)
