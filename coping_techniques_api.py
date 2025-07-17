from datetime import datetime, date
from firebase_admin import firestore
from flask import Blueprint, jsonify, request

coping_techniques_bp = Blueprint('coping_techniques', __name__)



@coping_techniques_bp.route('/daily_summary_and_coping', methods=['GET'])
def daily_summary_and_coping():
    """
    For the current user, get today's messages from the latest bot session, generate a summary, and suggest coping techniques using DeepSeek.
    Query param: user_id (required)
    """
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    db = firestore.client()
    today_str = date.today().isoformat()

    # Find latest session for this user
    sessions_ref = db.collection('sessions').stream()
    latest_session = None
    latest_time = None
    for doc in sessions_ref:
        session = doc.to_dict()
        if session.get('user_id', '') == user_id or doc.id.startswith(user_id + "_"):
            # Find the latest session by last_updated or message timestamp
            last_time = None
            if 'last_updated' in session:
                try:
                    last_time = session['last_updated']
                    if isinstance(last_time, str):
                        last_time = datetime.fromisoformat(last_time)
                except:
                    last_time = None
            elif 'messages' in session and session['messages']:
                try:
                    last_time = datetime.fromisoformat(session['messages'][-1]['timestamp'])
                except:
                    last_time = None
            if last_time and (latest_time is None or last_time > latest_time):
                latest_time = last_time
                latest_session = session

    if not latest_session or 'messages' not in latest_session:
        return jsonify({'error': 'No session messages found for today'}), 404

    # Filter messages for today
    todays_messages = [
        m['message'] for m in latest_session['messages']
        if 'timestamp' in m and m['timestamp'].startswith(today_str)
    ]
    # Immediate support options (same as get_coping_techniques_and_support)
    support_options = [
        {
            "icon": "📞",
            "title": "National Suicide Prevention Lifeline",
            "subtitle": "24/7 Crisis Support",
            "contact": "988",
            "description": "Free and confidential emotional support",
            "action": "Call Now"
        },
        {
            "icon": "💬",
            "title": "Crisis Text Line",
            "subtitle": "Text Support Available",
            "contact": "741741",
            "description": "Text HOME to connect with a crisis counselor",
            "action": "Call Now"
        },
        {
            "icon": "🏥",
            "title": "SAMHSA National Helpline",
            "subtitle": "Mental Health & Substance Abuse",
            "contact": "1-800-662-4357",
            "description": "Treatment referral and information service",
            "action": "Call Now"
        }
    ]
    if not todays_messages:
        return jsonify({
            'coping_techniques': [],
            'immediate_support': support_options,
        }), 200

    transcript = "\n".join(todays_messages)

    # Generate summary using DeepSeek
    summary_prompt = f"""
You are a mental health assistant. Summarize the following conversation from today in 2 lines, focusing on the user's main issue and emotional state. Avoid direct quotes.\n\nConversation:\n{transcript}\n\n2-line summary:\n"""
    try:
        from openai import OpenAI
        deepseek_client = OpenAI(base_url="https://api.deepseek.com/v1", api_key="sk-09e270ba6ccb42f9af9cbe92c6be24d8")
        summary_response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.5,
            max_tokens=100
        )
        summary = summary_response.choices[0].message.content.strip()
    except Exception as e:
        return jsonify({'error': f'Failed to generate summary: {str(e)}'}), 500

    # Suggest coping techniques based on summary
    coping_prompt = f"""
You are a therapy assistant. Based on the following summary, suggest 2-3 coping techniques (by name only) that would help the user today. Only return a JSON list of technique names.\n\nSummary:\n{summary}\n\nCoping techniques:\n"""
    try:
        coping_response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": coping_prompt}],
            temperature=0.7,
            max_tokens=60
        )
        import json as _json
        # Try to parse the response as a JSON list
        coping_techniques = coping_response.choices[0].message.content.strip()
        try:
            coping_techniques = _json.loads(coping_techniques)
        except:
            # Fallback: try to extract as a list from text, removing markdown and bracket artifacts
            lines = [line.strip('-• ",') for line in coping_techniques.split('\n') if line.strip()]
            # Remove common markdown and bracket artifacts
            artifacts = {'```json', '```', '[', ']'}
            coping_techniques = [line for line in lines if line and line not in artifacts]
    except Exception as e:
        return jsonify({'error': f'Failed to generate coping techniques: {str(e)}'}), 500

    # Technique details mapping (only name, description, category)
    TECHNIQUE_DETAILS = {
        "5-4-3-2-1 Grounding": {
            "name": "5-4-3-2-1 Grounding",
            "description": "Name 5 things you see, 4 you hear, 3 you touch, 2 you smell, 1 you taste.",
            "category": "Anxiety"
        },
        "Box Breathing": {
            "name": "Box Breathing",
            "description": "Inhale for 4, hold for 4, exhale for 4, hold for 4.",
            "category": "Anxiety"
        },
        "Grief Stages": {
            "name": "Grief Stages",
            "description": "Acknowledge denial, anger, bargaining, depression, acceptance.",
            "category": "Breakup"
        },
        "Inner Critic Reframe": {
            "name": "Inner Critic Reframe",
            "description": "Ask yourself: What would I tell my best friend in this situation?",
            "category": "Self-worth"
        },
        "Safe Space Visualization": {
            "name": "Safe Space Visualization",
            "description": "Create a mental refuge to feel safe and calm.",
            "category": "Trauma"
        },
        "Boundary Scripts": {
            "name": "Boundary Scripts",
            "description": "Practice saying: 'I understand you feel that way, but I need to...'.",
            "category": "Family"
        },
        "Triage Method": {
            "name": "Triage Method",
            "description": "Sort tasks into Urgent, Important, Can Wait.",
            "category": "Crisis"
        },
        "Journaling": {
            "name": "Journaling",
            "description": "Write down your thoughts and feelings to process emotions and gain clarity.",
            "category": "Self-reflection"
        },
        "Mindful Breathing": {
            "name": "Mindful Breathing",
            "description": "Focus on your breath, inhaling and exhaling slowly to calm your mind and body.",
            "category": "Anxiety"
        },
        "Grounding Techniques": {
            "name": "Grounding Techniques",
            "description": "Use sensory awareness to connect with the present moment and reduce distress.",
            "category": "Anxiety"
        },
        "Deep Breathing": {
            "name": "Deep Breathing",
            "description": "Take slow, deep breaths to calm your nervous system and reduce stress.",
            "category": "Anxiety"
        },
        "Mindfulness Meditation": {
            "name": "Mindfulness Meditation",
            "description": "Practice being present in the moment, observing thoughts and feelings without judgment.",
            "category": "Mindfulness"
        }
    }

    # Map names to details, fallback to generic if not found
    detailed_techniques = []
    for name in coping_techniques:
        if name in TECHNIQUE_DETAILS:
            detailed_techniques.append(TECHNIQUE_DETAILS[name])
        else:
            # Generate description and category using DeepSeek
            try:
                info_prompt = f"""
You are a therapy assistant. For the coping technique '{name}', provide:
1. A one-sentence description of what it is and how it helps.
2. The most relevant category (e.g., Anxiety, Mindfulness, Self-reflection, Crisis, Trauma, etc.).
Return a JSON object with 'description' and 'category'.
"""
                info_response = deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": info_prompt}],
                    temperature=0.5,
                    max_tokens=60
                )
                import json as _json
                info_content = info_response.choices[0].message.content.strip()
                try:
                    info_json = _json.loads(info_content)
                    description = info_json.get("description", "See app for details.")
                    category = info_json.get("category", "General")
                except:
                    # Fallback: parse manually
                    description = info_content.split('"description"')[1].split(':')[1].split(',')[0].strip(' "') if '"description"' in info_content else "See app for details."
                    category = info_content.split('"category"')[1].split(':')[1].split('}')[0].strip(' "') if '"category"' in info_content else "General"
            except Exception:
                description = "See app for details."
                category = "General"
            detailed_techniques.append({
                "name": name,
                "description": description,
                "category": category
            })

    # Immediate support options (same as get_coping_techniques_and_support)
    support_options = [
        {
            "icon": "📞",
            "title": "National Suicide Prevention Lifeline",
            "subtitle": "24/7 Crisis Support",
            "contact": "988",
            "description": "Free and confidential emotional support",
            "action": "Call Now"
        },
        {
            "icon": "💬",
            "title": "Crisis Text Line",
            "subtitle": "Text Support Available",
            "contact": "741741",
            "description": "Text HOME to connect with a crisis counselor",
            "action": "Call Now"
        },
        {
            "icon": "🏥",
            "title": "SAMHSA National Helpline",
            "subtitle": "Mental Health & Substance Abuse",
            "contact": "1-800-662-4357",
            "description": "Treatment referral and information service",
            "action": "Call Now"
        }
    ]

    return jsonify({
        'coping_techniques': detailed_techniques,
        'immediate_support': support_options
    })
