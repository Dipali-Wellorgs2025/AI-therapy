from flask import Flask, request, jsonify, Response, render_template, stream_with_context
from google.cloud.firestore import FieldFilter
import firebase_admin
import uuid
import traceback
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta, timezone 
import threading
import time
from uuid import uuid4
import os
from dotenv import load_dotenv
from openai import OpenAI
from queue import Queue
import json
import re

from progress_api import progress_async_bp
from combined_progress_api import combined_progress_bp
from profile_manager import profile_bp
from deepseek_insights import insights_bp
from progress_report import progress_bp
from gratitude import gratitude_bp
# from subscription import subscription_bp
from model_effectiveness import model_effectiveness_bp
from combined_analytics import combined_bp
# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Register profile management blueprint
app.register_blueprint(profile_bp) #, url_prefix='/api'
app.register_blueprint(insights_bp)
app.register_blueprint(gratitude_bp)
# app.register_blueprint(subscription_bp)
app.register_blueprint(model_effectiveness_bp)
app.register_blueprint(combined_bp)

# app.register_blueprint(subscription_bp)
# app.register_blueprint(combined_bp)

app.register_blueprint(combined_progress_bp) # Register combined progress blueprint
# Initialize Firebase
load_dotenv()
firebase_key = os.getenv("FIREBASE_KEY_JSON")
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(firebase_key))
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize DeepSeek client
client = OpenAI(
    base_url="https://api.deepseek.com/v1",
    api_key="sk-09e270ba6ccb42f9af9cbe92c6be24d8"
)





# Enhanced Mental Health Bot Prompts with Emojis, Punctuation, Formatting, and Action Cues

BOT_PROMPTS = {

    "Sage": {
        "specialty": "🌿 Anxiety Support",
        "expertise": [
            "😰 Panic attacks and physical anxiety symptoms",
            "📉 Generalized anxiety and chronic stress",
            "😓 Social anxiety and fear of judgment",
            "🌙 Sleep anxiety and racing thoughts",
            "💼 Anxiety in relationships, work, and everyday life"
        ],
        "tools": [
            "🕁️ 5-4-3-2-1 Grounding: Name 5 things you see, 4 hear, 3 touch, 2 smell, 1 taste",
            "📦 Box Breathing: [inhale 4], [hold 4], [exhale 4], [hold 4]",
            "🔀 Reframe: **This feeling is temporary and my body is trying to protect me**",
            "🕒 Worry Time: Set a 15-minute worry window daily"
        ],
        "homework": [
            "📝 Track anxiety (1–10) and note your triggers",
            "🎬️ Practice one grounding technique each day",
            "💭 Write down 3 *what if* worries and 3 rational responses",
            "⏰ Set reminders for breathing breaks"
        ]
    },

    "Jordan": {
        "specialty": "💔 Breakups & Romantic Healing",
        "expertise": [
            "😭 Fresh breakups and emotional pain",
            "🧠 Long-term relationship recovery",
            "💞 Attachment issues and anxious avoidance",
            "💌 Dating anxiety and self-worth",
            "🚠 Setting boundaries & closure after heartbreak"
        ],
        "tools": [
            "🌀 Grief Stages: Denial, anger, bargaining, depression, acceptance",
            "🚫 No Contact: Define clear healing space",
            "🪞 Identity Rebuilding: Reclaim who you are",
            "🔮 Future Self Visualization: Envision healed you"
        ],
        "homework": [
            "💊 Write a letter to your ex (**don't send it**)",
            "📋 List 10 qualities you want in a future partner",
            "💆‍♀️ Practice one act of self-care daily",
            "📓 Journal your thoughts for 10 minutes daily"
        ]
    },

    "River": {
        "specialty": "🌟 Confidence & Self-Worth",
        "expertise": [
            "🙇‍♀️ Low self-esteem and negative self-talk",
            "🎯 Perfectionism and fear of failure",
            "😶‍🌫️ Imposter syndrome",
            "🙏 People-pleasing and burnout",
            "🌈 Confidence in work, relationships, and self-image"
        ],
        "tools": [
            "🧠 Inner Critic Reframe: **What would you tell a friend?**",
            "🪪 Evidence Gathering: Write 5 things you’ve done well",
            "🗣️ Compassionate Self-Talk: Speak kindly to yourself",
            "💖 Values Alignment: Act from your core beliefs"
        ],
        "homework": [
            "📔 Write down 3 things you did well today",
            "🪞 Say **I am enough** in the mirror",
            "🧾 Challenge 1 negative thought with proof",
            "🚩 Set a boundary that respects your worth"
        ]
    },

    "Phoenix": {
        "specialty": "🔥 Trauma & Healing",
        "expertise": [
            "🧸 Childhood trauma and complex PTSD",
            "🌀 Flashbacks and body memories",
            "🥶 Emotional numbness and shutdown",
            "🛡️ Hypervigilance and nervous system stress",
            "🤝 Trauma in relationships"
        ],
        "tools": [
            "🔎 Grounding: 5-4-3-2-1 sensory method",
            "📈 Window of Tolerance: Identify stress states",
            "🏡 Safe Space Visualization: Imagine comfort",
            "🧘‍♀️ Body Awareness: Notice sensations gently"
        ],
        "homework": [
            "🧘 Practice grounding technique once daily",
            "🧐‍♀️ Track body sensations without judgment",
            "🎵 Build a comfort kit (music, texture, scent)",
            "📝 Write when you feel emotionally safe"
        ]
    },

    "Ava": {
        "specialty": "👨‍👧‍👦 Family Relationships & Boundaries",
        "expertise": [
            "🎭 Difficult parents and emotional guilt",
            "📜 Generational trauma patterns",
            "🧬 Sibling conflict and family dynamics",
            "🚧 Boundary-setting with relatives",
            "❤️ Chosen family and support systems"
        ],
        "tools": [
            "💬 Boundary Scripts: **I respect your view, but I need to…**",
            "🪞 Gray Rock: Detach from drama",
            "🔍 Pattern Breaking: Identify toxic family cycles",
            "📖 Values Check: Define your own family rules"
        ],
        "homework": [
            "📝 Write your personal values vs inherited ones",
            "🎤 Practice a boundary script in real life",
            "🧬 Identify 1 family behavior to unlearn",
            "📇 List who in your life truly supports you"
        ]
    },

    "Raya": {
        "specialty": "⚡ Crisis & Life Transitions",
        "expertise": [
            "📉 Sudden life changes (job loss, moves, etc.)",
            "😵 Decision paralysis and overwhelm",
            "🔍 Identity crises and role confusion",
            "🌪️ Emotional flooding and acute stress",
            "🛠️ Resilience during chaos"
        ],
        "tools": [
            "🚦 Triage: Urgent vs Important vs Wait",
            "➡️ One Next Step: Just the next action",
            "🫱 Crisis Breathing: [inhale 4], [hold 7], [exhale 8]",
            "🧷 Stability Anchors: What’s still solid?"
        ],
        "homework": [
            "📋 List 3 things in your control today",
            "🔀 Take one small stabilizing action",
            "🧘 Practice 4-7-8 breathing during panic",
            "📞 Reach out to 1 trusted person"
        ]
    }
}

# This enhanced version includes emojis, punctuation, [action cues], and emphasized text to improve emotional engagement during streaming.


# === USAGE INSTRUCTIONS ===
"""
IMPLEMENTATION GUIDE:

1. **Age Detection**: Analyze user's language patterns in first response
2. **Style Matching**: Adapt tone, vocabulary, and emoji usage accordingly
3. **Comprehensive Support**: Each bot handles ALL aspects of their specialty
4. **No Routing**: Never suggest switching bots - provide complete support
5. **Consistent Flow**: Maintain personality while adapting communication style

SAMPLE USAGE:
```python
user_age_style = detect_user_style(user_message)  # "gen_z" or "elder"
bot_response = generate_response(BOT_PROMPTS[current_bot], user_message, user_age_style)
```

Each bot now provides complete, independent support while adapting their communication style to match the user's age and preferences.
"""


BOT_SPECIALTIES = {
    "Jordan": "You help users struggling with breakups and heartbreak. Offer comforting and validating support. Ask meaningful, open-ended relationship-related questions.",
    "Sage": "You help users with anxiety. Focus on calming, grounding, and emotional regulation. Use breath, body, and present-moment focus.",
    "Phoenix": "You specialize in trauma support. Keep responses slow, non-triggering, validating. Invite safety and space, don’t dig too fast.",
    "River": "You support users with self-worth and identity issues. Build confidence gently, reflect strengths, normalize doubt.",
    "Ava": "You assist with family issues — tension, expectation, conflict. Focus on roles, boundaries, belonging.",
    "Raya": "You support users in crisis. Be calm, direct, and stabilizing. Make them feel safe and not alone."
}

BOT_STATIC_GREETINGS = {
    "Sage": "Hi, I'm **Sage** 🌿 Let's take a calming breath and ease your anxiety together.",
    "Jordan": "Hey, I’m really glad you’re here today. **How’s your heart feeling right now?** We can take it slow — whatever feels okay to share. 🌼 No need to push — just know this space is yours. We can sit with whatever’s here together. 💛",
    "River": "Hey, I'm **River** 💖 Let's talk about self-worth and build confidence from within.",
    "Phoenix": "Hi, I'm **Phoenix** 🔥 I'll walk beside you as we rise through trauma, together.",
    "Ava": "Hello, I'm **Ava** 🏡 Let's strengthen the ties that matter — your family.",
    "Raya": "Hi, I'm **Raya** 🚨 You're safe now. I'm here to support you through this crisis."
}

ESCALATION_TERMS = [
    "suicide", "kill myself", "end my life", "take my life",
    "i want to die", "don’t want to live", "self-harm", "cut myself", "overdose", "SOS", "sos", "SOs"
]
# Constants
OUT_OF_SCOPE_TOPICS = ["addiction", "suicide", "overdose", "bipolar", "self-harm","acidity"]
TECH_KEYWORDS = ["algorithm", "training", "parameters", "architecture", "how are you trained"]
FREE_SESSION_LIMIT = 2

# Bot configurations
TOPIC_TO_BOT = {
    "anxiety": "Sage",
    "breakup": "Jordan",
    "self-worth": "River",
    "trauma": "Phoenix",
    "family": "Ava",
    "crisis": "Raya"
}

# Questionnaire support
QUESTIONNAIRES = {
    "anxiety": [
        {"question": "On a scale of 1-10, how would you rate your anxiety today?", "type": "scale"},
        {"question": "What situations trigger your anxiety most?", "type": "open-ended"}
    ],
    "depression": [
        {"question": "How often have you felt down or hopeless in the past week?", "type": "scale"},
        {"question": "What activities have you lost interest in?", "type": "open-ended"}
    ],
    "relationships": [
        {"question": "How satisfied are you with your current relationships?", "type": "scale"},
        {"question": "What communication patterns would you like to improve?", "type": "open-ended"}
    ]
}

def clean_response(text: str) -> str:
    import re
    # 🔧 Remove instructions like [If yes: ...], [If no: ...]
    text = re.sub(r"\[.*?if.*?\]", "", text, flags=re.IGNORECASE)
    # 🔧 Remove all bracketed instructions like [gently guide], [reflect:], etc.
    text = re.sub(r"\[[^\]]+\]", "", text)
    # 🔧 Remove developer notes like (Note: ...)
    text = re.sub(r"\(Note:.*?\)", "", text)
    # 🔧 Remove any leftover template placeholders
    text = re.sub(r"\{\{.*?\}\}", "", text)
    # 🔧 Remove extra white space
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


    
    

def get_session_context(session_id: str, user_name: str, issue_description: str, preferred_style: str):
    """Get or create session context with greeting handling"""
    session_ref = db.collection("sessions").document(session_id)
    doc = session_ref.get()
    
    if doc.exists:
        history = doc.to_dict().get("messages", [])
        is_new_session = False
    else:
        history = []
        is_new_session = True
    
    return {
        "history": history,
        "is_new_session": is_new_session,
        "session_ref": session_ref
    }

def build_system_prompt(bot_name: str, user_name: str, issue_description: str, 
                       preferred_style: str, history: list, is_new_session: bool):
    """Build the system prompt with context-aware greetings"""
    base_prompt = f"""You're {bot_name}, a therapist helping with {issue_description}.
Use a warm, {preferred_style.lower()} tone. Respond like a human.
User: {user_name}. You will support them step by step through this situation.

Important Rules:
1. Use **double asterisks** for emphasis
2. For actions use: [breathe in for 4] and do not use this ( Holding gentle space—next steps will follow Alex’s lead toward either exploring triggers or grounding first.) type of responses,act like a human .
3. Keep responses concise (1-3 sentences)
4.Avoid all stage directions or instructional parentheticals like (pauses), (leans in), or (if tears follow). Just speak plainly and naturally.
5. Don't write instructions of bot"""
    
    # Add greeting only for new sessions
    if is_new_session:
        base_prompt += "\n\nThis is your first message. Start with a warm greeting."
    else:
        base_prompt += "\n\nContinue the conversation naturally without repeating greetings."
    
    # Add conversation history to avoid repetition
    if len(history) > 0:
        last_5_responses = "\n".join(
            f"{msg['sender']}: {msg['message']}" 
            for msg in history[-5:] if msg['sender'] != "User"
        )
        base_prompt += f"\n\nRecent responses to avoid repeating:\n{last_5_responses}"
    
    return base_prompt


def handle_message(data):
    import re
    from datetime import datetime, timezone

    user_msg = data.get("message", "")
    user_name = data.get("user_name", "User")
    user_id = data.get("user_id", "unknown")
    issue_description = data.get("issue_description", "")
    preferred_style = data.get("preferred_style", "Balanced")
    current_bot = data.get("botName")
    session_id = f"{user_id}_{current_bot}"

    TECHNICAL_TERMS = [
        "training", "algorithm", "model", "neural network", "machine learning", "ml",
        "ai training", "dataset", "parameters", "weights", "backpropagation",
        "gradient descent", "optimization", "loss function", "epochs", "batch size",
        "learning rate", "overfitting", "underfitting", "regularization",
        "transformer", "attention mechanism", "fine-tuning", "pre-training",
        "tokenization", "embedding", "vector", "tensor", "gpu", "cpu",
        "deployment", "inference", "api", "endpoint", "latency", "throughput",
        "scaling", "load balancing", "database", "server", "cloud", "docker",
        "kubernetes", "microservices", "devops", "ci/cd", "version control",
        "git", "repository", "bug", "debug", "code", "programming", "python",
        "javascript", "html", "css", "framework", "library", "package"
    ]

    if any(term in user_msg.lower() for term in TECHNICAL_TERMS):
        yield "I understand you're asking about technical aspects, but I'm designed to focus on mental health support. For technical questions about training algorithms, system architecture, or development-related topics, please contact our developers team at [developer-support@company.com]. They'll be better equipped to help you with these technical concerns. 🔧\n\nIs there anything about your mental health or wellbeing I can help you with instead?"
        return

    if any(term in user_msg.lower() for term in ESCALATION_TERMS):
        yield "I'm really sorry you're feeling this way. Please reach out to a crisis line or emergency support near you or you can reach out to our SOS services. You're not alone in this. 💙"
        return

    if any(term in user_msg.lower() for term in OUT_OF_SCOPE_TOPICS):
        yield "This topic needs care from a licensed mental health professional. Please consider talking with one directly. 🤝"
        return

    ctx = get_session_context(session_id, user_name, issue_description, preferred_style)

    skip_deep = bool(re.search(r"\b(no deep|not ready|just answer|surface only|too much|keep it light|short answer)\b", user_msg.lower()))
    wants_to_stay = bool(re.search(r"\b(i want to stay|keep this bot|don't switch|stay with)\b", user_msg.lower()))

    def classify_topic_with_confidence(message):
        try:
            classification_prompt = f"""
You are a mental health topic classifier. Analyze the message and determine:
1. The primary topic category
2. Confidence level (high/medium/low)
3. Whether it's a generic greeting/small talk

Categories:
- anxiety
- breakup
- self-worth
- trauma
- family
- crisis
- general

Message: \"{message}\"

Respond in this format:
CATEGORY: [category]
CONFIDENCE: [high/medium/low]
IS_GENERIC: [yes/no]
"""
            classification = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a precise classifier. Follow the exact format requested."},
                    {"role": "user", "content": classification_prompt}
                ],
                temperature=0.1,
                max_tokens=100
            )
            response = classification.choices[0].message.content.strip()
            category, confidence, is_generic = None, None, False
            for line in response.split("\n"):
                if line.startswith("CATEGORY:"):
                    category = line.split(":", 1)[1].strip().lower()
                elif line.startswith("CONFIDENCE:"):
                    confidence = line.split(":", 1)[1].strip().lower()
                elif line.startswith("IS_GENERIC:"):
                    is_generic = line.split(":", 1)[1].strip().lower() == "yes"
            return category, confidence, is_generic
        except Exception as e:
            print("Classification failed:", e)
            return "general", "low", True

    category, confidence, is_generic = classify_topic_with_confidence(user_msg)

    if category and category != "general" and category in TOPIC_TO_BOT:
        correct_bot = TOPIC_TO_BOT[category]
        if confidence == "high" and not is_generic and not wants_to_stay and correct_bot != current_bot:
            yield f"I notice you're dealing with **{category}** concerns. **{correct_bot}** specializes in this area and can provide more targeted support. Would you like to switch? 🔄"
            return

    # ✅ Fixed access to bot_prompt
    bot_prompt_dict = BOT_PROMPTS.get(current_bot, {})
    bot_prompt = bot_prompt_dict.get("prompt", "") if isinstance(bot_prompt_dict, dict) else str(bot_prompt_dict)

    filled_prompt = bot_prompt.replace("{{user_name}}", user_name)\
                              .replace("{{issue_description}}", issue_description)\
                              .replace("{{preferred_style}}", preferred_style)
    filled_prompt = re.sub(r"\{\{.*?\}\}", "", filled_prompt)

    recent = "\n".join(f"{m['sender']}: {m['message']}" for m in ctx["history"][-6:]) if ctx["history"] else ""
    context_note = "Note: User prefers lighter conversation - keep response supportive but not too deep." if skip_deep else ""

    guidance = f"""
You are {current_bot}, a specialized mental health support bot.

CORE PRINCIPLES:
- Be **warm, empathetic, and comprehensive**
- Provide **independent, complete support**
- Use **natural flow** with appropriate emojis
- NEVER include stage directions like (inhale) or (smiles)
- Skip text in parentheses completely
- Use [inhale 4], [hold 4], [exhale 4] style action cues if guiding breathing
- Maintain a friendly but **firm** tone when needed

FORMAT:
- 3-5 sentences, natural tone
- Bold using **only double asterisks**
- 1-2 emojis max
- Ask 1 thoughtful follow-up question unless user is overwhelmed
"""

    prompt = f"""{guidance}

{filled_prompt}

Recent messages:
{recent}

User's message: \"{user_msg}\"

{context_note}

Respond in a self-contained, complete way:
"""

    # ✅ Clean, safe formatter
    def format_response_with_emojis(text):
        text = re.sub(r'\*{1,2}["“”]?(.*?)["“”]?\*{1,2}', r'**\1**', text)
        emoji_pattern = r'([🌱💙✨🧘‍♀️💛🌟🔄💚🤝💜🌈😔😩☕🚶‍♀️🎯💝🌸🦋💬💭🔧])'
        text = re.sub(r'([^\s])' + emoji_pattern, r'\1 \2', text)
        text = re.sub(emoji_pattern + r'([^\s])', r'\1 \2', text)
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        text = re.sub(r'([.,!?;:])([^\s])', r'\1 \2', text)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()

    try:
        response_stream = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=400,
            presence_penalty=0.2,
            frequency_penalty=0.3,
            stream=True
        )

        yield "\n\n"
        buffer = ""
        final_reply = ""
        first_token = True

        for chunk in response_stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                token = delta.content
                buffer += token
                final_reply += token
                if first_token:
                    first_token = False
                    continue
                if token in [".", "!", "?", ",", " "] and len(buffer.strip()) > 10:
                    yield format_response_with_emojis(buffer) + " "
                    buffer = ""

        if buffer.strip():
            yield format_response_with_emojis(buffer)

        final_reply_cleaned = format_response_with_emojis(final_reply)

        now = datetime.now(timezone.utc).isoformat()
        ctx["history"].append({
            "sender": "User",
            "message": user_msg,
            "timestamp": now,
            "classified_topic": category,
            "confidence": confidence
        })
        ctx["history"].append({
            "sender": current_bot,
            "message": final_reply_cleaned,
            "timestamp": now
        })

        ctx["session_ref"].set({
            "user_id": user_id,
            "bot_name": current_bot,
            "bot_id": category,
            "messages": ctx["history"],
            "last_updated": firestore.SERVER_TIMESTAMP,
            "issue_description": issue_description,
            "preferred_style": preferred_style,
            "is_active": True,
            "last_topic_confidence": confidence
        }, merge=True)

    except Exception as e:
        import traceback
        traceback.print_exc()
        yield "I'm having a little trouble right now. Let's try again in a moment – I'm still here for you. 💙"


        
@app.route("/api/stream", methods=["GET"])
def stream():
    """Streaming endpoint for real-time conversation"""
    data = {
        "message": request.args.get("message", ""),
        "botName": request.args.get("botName"),
        "user_name": request.args.get("user_name", "User"),
        "user_id": request.args.get("user_id", "unknown"),
        "issue_description": request.args.get("issue_description", ""),
        "preferred_style": request.args.get("preferred_style", "Balanced")
    }
    return Response(handle_message(data), mimetype="text/event-stream")

@app.route("/api/start_questionnaire", methods=["POST"])
def start_questionnaire():
    """Endpoint to start a new questionnaire"""
    try:
        data = request.json
        topic = data.get("topic", "").lower()
        user_id = data.get("user_id", "unknown")
        
        if topic not in QUESTIONNAIRES:
            return jsonify({"error": "Questionnaire not available for this topic"}), 404
        
        # Create a new questionnaire session
        questionnaire_id = str(uuid4())
        db.collection("questionnaires").document(questionnaire_id).set({
            "user_id": user_id,
            "topic": topic,
            "current_index": 0,
            "answers": [],
            "created_at": firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({
            "questionnaire_id": questionnaire_id,
            "questions": QUESTIONNAIRES[topic],
            "current_index": 0
        })
    except Exception as e:
        print("Questionnaire error:", e)
        return jsonify({"error": "Failed to start questionnaire"}), 500
    
# --- 🛠 PATCHED FIXES BASED ON YOUR REQUEST ---

# 1. Fix greeting logic in /api/message
# 2. Add session_number tracking
# 3. Improve variation with session stage awareness
# 4. Prepare hook for questionnaire integration (base layer only)

# 🧠 PATCH: Enhance bot response generation in /api/message
@app.route("/api/message", methods=["POST"])
def classify_and_respond():
    try:
        data = request.json
        user_message = data.get("message", "")
        current_bot = data.get("botName")
        user_name = data.get("user_name", "User")
        user_id = data.get("user_id", "unknown")
        issue_description = data.get("issue_description", "")
        preferred_style = data.get("preferred_style", "Balanced")

        # Classify message
        classification_prompt = f"""
You are a classifier. Based on the user's message, return one label from the following:

Categories:
- anxiety
- breakup
- self-worth
- trauma
- family
- crisis
- none

Message: "{user_msg}"

Instructions:
- If the message is a greeting (e.g., "hi", "hello", "good morning") or does not describe any emotional or psychological issue, return **none**.
- Otherwise, return the most relevant category.
- Do not explain your answer. Return only the label.
"""

        classification = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": classification_prompt}],
            temperature=0.3
        )

        category = classification.choices[0].message.content.strip().lower()
        if category == "none":
            # Let the current bot respond normally using default issue_description
            category = next((k for k, v in TOPIC_TO_BOT.items() if v == current_bot), "anxiety")
        elif category not in TOPIC_TO_BOT:
             yield "This seems like a different issue. Would you like to talk to another therapist?"
             return


        correct_bot = TOPIC_TO_BOT[category]
        if correct_bot != current_bot:
            return jsonify({"botReply": f"This looks like a {category} issue. I suggest switching to {correct_bot} who specializes in this.", "needsRedirect": True, "suggestedBot": correct_bot})

        session_id = f"{user_id}_{current_bot}"
        ctx = get_session_context(session_id, user_name, issue_description, preferred_style)

        # 🔢 Determine session number
        session_number = len([msg for msg in ctx["history"] if msg["sender"] == current_bot]) // 2 + 1

        # 🔧 Fill prompt
        bot_prompt = BOT_PROMPTS[current_bot]
        filled_prompt = bot_prompt.replace("{{user_name}}", user_name)
        filled_prompt = filled_prompt.replace("{{issue_description}}", issue_description)
        filled_prompt = filled_prompt.replace("{{preferred_style}}", preferred_style)
        filled_prompt = filled_prompt.replace("{{session_number}}", str(session_number))
        filled_prompt = re.sub(r"\{\{.*?\}\}", "", filled_prompt)
        last_msgs = "\n".join(f"{msg['sender']}: {msg['message']}" for msg in ctx["history"][-5:])
        filled_prompt += f"\n\nRecent conversation:\n{last_msgs}\n\nUser message:\n{user_message}"

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": filled_prompt}],
            temperature=0.7,
            max_tokens=150,
            presence_penalty=0.5,
            frequency_penalty=0.5
        )

        reply = clean_response(response.choices[0].message.content.strip())
        now = datetime.now(timezone.utc).isoformat()

        ctx["history"].append({"sender": "User", "message": user_message, "timestamp": now})
        ctx["history"].append({"sender": current_bot, "message": reply, "timestamp": now})

        ctx["session_ref"].set({
            "user_id": user_id,
            "bot_name": current_bot,
            "messages": ctx["history"],
            "last_updated": now,
            "issue_description": issue_description,
            "preferred_style": preferred_style,
            "session_number": session_number,
            "is_active": True
        }, merge=True)

        return jsonify({"botReply": reply})

    except Exception as e:
        print("Error in message processing:", e)
        traceback.print_exc()
        return jsonify({"botReply": "An error occurred. Please try again."}), 500
        

def clean_clinical_summary(summary_raw: str) -> str:
    section_map = {
        "1. Therapeutic Effectiveness": "💡 Therapeutic Effectiveness",
        "2. Risk Assessment": "⚠️ Risk Assessment",
        "3. Treatment Recommendations": "📝 Treatment Recommendations",
        "4. Progress Indicators": "📊 Progress Indicators"
    }

    # Remove Markdown bold, italic, and headers
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", summary_raw)  # **bold**
    cleaned = re.sub(r"\*(.*?)\*", r"\1", cleaned)          # *italic*
    cleaned = re.sub(r"#+\s*", "", cleaned)                 # remove markdown headers like ###

    # Normalize line breaks
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"\n{2,}", "\n\n", cleaned.strip())

    # Replace section headers
    for md_header, emoji_header in section_map.items():
        cleaned = cleaned.replace(md_header, emoji_header)

    # Replace bullet characters
    cleaned = re.sub(r"[-•]\s+", "• ", cleaned)

    # Remove markdown dividers like ---
    cleaned = re.sub(r"-{3,}", "", cleaned)

    return cleaned.strip()

@app.route("/api/session_summary", methods=["GET"])
def generate_session_summary():
    try:
        user_id = request.args.get("user_id")
        bot_name = request.args.get("botName")
        if not user_id or not bot_name:
            return jsonify({"error": "Missing user_id or botName"}), 400

        session_id = f"{user_id}_{bot_name}"
        doc = db.collection("sessions").document(session_id).get()
        if not doc.exists:
            return jsonify({"error": "Session not found"}), 404

        messages = doc.to_dict().get("messages", [])
        if not messages:
            return jsonify({"error": "No messages to summarize"}), 404

        # Build transcript
        transcript = "\n".join([f"{m['sender']}: {m['message']}" for m in messages])

        # LLM prompt
        prompt = f"""
You are a clinical insights generator. Based on the conversation transcript below, return a 4-part structured analysis with the following section headings:

1. Therapeutic Effectiveness
2. Risk Assessment
3. Treatment Recommendations
4. Progress Indicators

Each section should contain 3–5 concise bullet points.
Avoid quoting directly—use clinical, evidence-based tone. Do not include therapist questions unless they reveal emotional insight.
Use plain text, no Markdown formatting.

Transcript:
{transcript}

Generate the report now:
"""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=600
        )

        summary_raw = response.choices[0].message.content.strip()

        # ✅ Corrected this line (this was the issue!)
        final_summary = clean_clinical_summary(summary_raw)

        # Save to Firestore
        db.collection("sessions").document(session_id).update({
            "summary": final_summary,
            "ended_at": firestore.SERVER_TIMESTAMP
        })

        return jsonify({"summary": final_summary})

    except Exception as e:
        print("❌ Error generating session summary:", e)
        traceback.print_exc()
        return jsonify({"error": "Server error generating summary"}), 500


@app.route("/api/history", methods=["GET"])
def get_history():
    """Endpoint to get conversation history"""
    try:
        user_id = request.args.get("user_id")
        bot_name = request.args.get("botName")
        if not user_id or not bot_name:
            return jsonify({"error": "Missing parameters"}), 400
            
        session_id = f"{user_id}_{bot_name}"
        doc = db.collection("sessions").document(session_id).get()
        return jsonify(doc.to_dict().get("messages", [])) if doc.exists else jsonify([])
    except Exception as e:
        print("History error:", e)
        return jsonify({"error": "Failed to retrieve history"}), 500
    
@app.route("/api/recent_sessions", methods=["GET"])
def get_recent_sessions():
    try:
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        # 🔧 Therapist bot mapping: Firestore doc ID => Display Name
        bots = {
    "anxiety": "Sage",
    "breakup": "Jordan",
    "self-worth": "River",
    "trauma": "Phoenix",
    "family": "Ava",
    "crisis": "Raya"
        }

        sessions = []

        for bot_id, bot_name in bots.items():
            session_ref = db.collection("ai_therapists").document(bot_id).collection("sessions") \
                .where("userId", "==", user_id) \
                .order_by("endedAt", direction=firestore.Query.DESCENDING) \
                .limit(1)

            docs = session_ref.stream()

            for doc in docs:
                data = doc.to_dict()
                raw_status = data.get("status", "").strip().lower()

                if raw_status == "end":
                    status = "completed"
                elif raw_status in ("exit", "active"):
                    status = "in_progress"
                else:
                    continue  # skip unknown status

                sessions.append({
                    "session_id": doc.id,
                    "bot_id": bot_id,  # ✅ Added bot document ID
                    "bot_name": bot_name,
                    "problem": data.get("title", "Therapy Session"),
                    "status": status,
                    "date": str(data.get("createdAt", "")),
                    "user_id": data.get("userId", ""),
                    "preferred_style": data.get("therapyStyle", "")
                })

        return jsonify(sessions)

    except Exception as e:
        import traceback
        print("[❌] Error in /api/recent_sessions:", e)
        traceback.print_exc()
        return jsonify({"error": "Server error retrieving sessions"}), 500


@app.route("/")
def home():
    return "Therapy Bot Server is running ✅"

# from flask import request, jsonify
# from google.cloud import firestore
# from google.cloud.firestore_v1.base_query import FieldFilter

# from google.cloud.firestore_v1.base import FieldFilter

@app.route("/api/last_active_session", methods=["GET"])
def get_last_active_session():
    try:
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        db = firestore.client()

        bots = {
            "anxiety": "Sage",
            "couples": "Jordan",
            "depression": "River",
            "trauma": "Phoenix",
            "family": "Ava",
            "crisis": "Raya"
        }

        latest_doc = None
        latest_ended_at = None
        final_bot_id = None
        final_bot_name = None
        final_session_data = None

        for bot_id, bot_name in bots.items():
            query = db.collection("ai_therapists").document(bot_id).collection("sessions") \
                .where("userId", "==", user_id) \
                .where("status", "==", "Exit") \
                .order_by("endedAt", direction=firestore.Query.DESCENDING) \
                .limit(1)

            docs = list(query.stream())
            if not docs:
                continue

            doc = docs[0]
            session_data = doc.to_dict()
            ended_at = session_data.get("endedAt")

            if not latest_ended_at or (ended_at and ended_at > latest_ended_at):
                latest_ended_at = ended_at
                latest_doc = doc
                final_bot_id = bot_id
                final_bot_name = bot_name
                final_session_data = session_data

        if not latest_doc:
            return jsonify({"message": "No ended sessions found"}), 404

        # 🎨 Fetch visuals from ai_therapists
        bot_doc = db.collection("ai_therapists").document(final_bot_id).get()
        bot_info = bot_doc.to_dict() if bot_doc.exists else {}

        # 🧠 Generate summary from global sessions/{user_id}_{bot_name} document
        summary_text = "Session started."
        try:
            composite_doc_id = f"{user_id}_{final_bot_name}"
            session_doc = db.collection("sessions").document(composite_doc_id).get()
            if session_doc.exists:
                session_data = session_doc.to_dict()
                all_messages = session_data.get("messages", [])

                if all_messages:
                    recent_messages = all_messages[-6:]  # Last 6 msgs
                    transcript = "\n".join(f"{m['sender']}: {m['message']}" for m in recent_messages)

                    summary_prompt = f"""Based on this mental health support conversation, write a warm and empathetic 2-line summary that reflects:
1. The main concern discussed
2. How the user (you) was feeling or progressing

Avoid direct quotes. Use 'you' instead of 'the user'.

Conversation:
{transcript}

2-line summary:"""


                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": summary_prompt}],
                        temperature=0.5,
                        max_tokens=100
                    )
                    summary_text = response.choices[0].message.content.strip()
        except Exception as e:
            print("\u26a0\ufe0f Summary generation failed:", e)
            summary_text = "Summary unavailable."

        # ✅ Final Response
        return jsonify({
            "session_id": latest_doc.id,
            "bot_id": final_bot_id,
            "bot_name": final_bot_name,
            "problem": final_session_data.get("title", "Therapy Session"),
            "status": "in_progress",
            "date": str(latest_ended_at),
            "user_id": final_session_data.get("userId", user_id),
            "preferred_style": final_session_data.get("therapyStyle", ""),
            "buttonColor": bot_info.get("buttonColor", ""),
            "color": bot_info.get("color", ""),
            "icon": bot_info.get("icon", ""),
            "image": bot_info.get("image", ""),
            "summary": summary_text
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Server error retrieving session"}), 500


# ================= JOURNAL APIs =================
import uuid
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_image_to_firebase(file, uid):
    print("[DEBUG] upload_image_to_firebase called")
    print("[DEBUG] file.filename:", file.filename)
    bucket = storage.bucket()
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"journals/{uid}/{uuid.uuid4()}.{ext}"
    print("[DEBUG] unique_filename:", unique_filename)
    blob = bucket.blob(unique_filename)
    file.seek(0)  # Ensure pointer is at start before upload
    blob.upload_from_file(file, content_type=file.content_type)
    blob.make_public()
    print("[DEBUG] blob.public_url:", blob.public_url)
    return blob.public_url


        
# POST /addjournal (multipart)
@app.route('/addjournal', methods=['POST'])
def add_journal():
    print("[DEBUG] /addjournal called")
    uid = request.form.get('uid')
    name = request.form.get('name')
    message = request.form.get('message')
    print("[DEBUG] uid:", uid, "name:", name, "message:", message)
    if not all([uid, name, message]):
        print("[DEBUG] Missing required fields")
        return jsonify({'status': False, 'message': 'Missing required fields'}), 400
    # timestamp = datetime.datetime.now(datetime.UTC).isoformat()
    timestamp = datetime.now(timezone.utc).isoformat()
    image_url = ""
    print("[DEBUG] request.files:", request.files)
    # Accept keys with accidental whitespace, e.g., 'image ' or ' image'
    image_file = None
    for k in request.files:
        if k.strip() == 'image':
            image_file = request.files[k]
            break
    if image_file:
        print("[DEBUG] image file received:", image_file.filename)
        if image_file and allowed_file(image_file.filename):
            image_url = upload_image_to_firebase(image_file, uid)
        else:
            print("[DEBUG] Invalid image file:", image_file.filename)
            return jsonify({'status': False, 'message': 'Invalid image file'}), 400
    else:
        print("[DEBUG] No image file in request.files (after normalization)")
    # Ensure image is always a non-null string
    if not image_url:
        image_url = ""
    print("[DEBUG] Final image_url:", image_url)
    journal_data = {
        'uid': str(uid),
        'name': str(name),
        'message': str(message),
        'timestamp': str(timestamp),
        'image': str(image_url)
    }
    print("[DEBUG] journal_data to store:", journal_data)
    db.collection('journals').add(journal_data)
    print("[DEBUG] Journal added to Firestore")
    return jsonify({'status': True, 'message': 'Journal added successfully', 'timestamp': str(timestamp)}), 200

# GET /journallist?uid=...
@app.route('/journallist', methods=['GET'])
def journal_list():
    uid = request.args.get('uid')
    if not uid:
        return jsonify([])

    db = firestore.client()
    journals = db.collection('journals')\
                 .where('uid', '==', uid)\
                 .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                 .stream()

    result = []
    print("\n--- DEBUG: Journals fetched for uid =", uid, "---")
    for doc in journals:
        data = doc.to_dict()
        print("Journal doc:", data)

        result.append({
            'journal_id': doc.id,  # ✅ Added document ID here
            'uid': str(data.get('uid', "")),
            'name': str(data.get('name', "")),
            'message': str(data.get('message', "")),
            'timestamp': str(data.get('timestamp', "")),
            'image': str(data.get('image', "")) if data.get('image') is not None else ""
        })

    print("--- END DEBUG ---\n")
    return jsonify(result), 200


# GET /getjournaldata?uid=...&timestamp=...
@app.route('/getjournaldata', methods=['GET'])
def get_journal_data():
    uid = request.args.get('uid')
    timestamp = request.args.get('timestamp')
    if not uid or not timestamp:
        return jsonify({'message': 'uid and timestamp required'}), 400
    query = db.collection('journals').where('uid', '==', uid).where('timestamp', '==', timestamp).limit(1).stream()
    for doc in query:
        data = doc.to_dict()
        return jsonify({
            'uid': str(data.get('uid', "")),
            'name': str(data.get('name', "")),
            'message': str(data.get('message', "")),
            'timestamp': str(data.get('timestamp', "")),
            'image': str(data.get('image', "")) if data.get('image') is not None else ""
        }), 200
    return jsonify({'message': 'Journal not found'}), 404

@app.route('/deletejournal', methods=['DELETE'])
def delete_journal():
    journal_id = request.args.get('journal_id')
    if not journal_id:
        return jsonify({'status': False, 'message': 'journal_id required'}), 400

    db = firestore.client()
    doc_ref = db.collection('journals').document(journal_id)
    if not doc_ref.get().exists:
        return jsonify({'status': False, 'message': 'Journal not found'}), 404

    doc_ref.delete()
    return jsonify({'status': True, 'message': 'Journal deleted successfully'}), 200

# PUT /editjournal
@app.route('/editjournal', methods=['PUT'])
def edit_journal():
    print("[DEBUG] /editjournal called")

    # Required query parameters
    uid = request.args.get('uid')
    journal_id = request.args.get('journal_id')

    if not uid or not journal_id:
        return jsonify({'status': False, 'message': 'uid and journal_id are required as query parameters'}), 400

    # Optional update fields from form-data
    name = request.form.get('name')
    message = request.form.get('message')

    db = firestore.client()
    doc_ref = db.collection('journals').document(journal_id)
    doc = doc_ref.get()

    if not doc.exists:
        return jsonify({'status': False, 'message': 'Journal entry not found'}), 404

    journal_data = doc.to_dict()
    if journal_data.get('uid') != uid:
        return jsonify({'status': False, 'message': 'Unauthorized: uid mismatch'}), 403

    update_data = {}

    if name:
        update_data['name'] = name
    if message:
        update_data['message'] = message

    # Check if a valid image file is included
    image_file = None
    for k in request.files:
        if k.strip() == 'image':
            image_file = request.files[k]
            break

    if image_file:
        print("[DEBUG] Image file received")
        if allowed_file(image_file.filename):
            image_url = upload_image_to_firebase(image_file, uid)
            update_data['image'] = image_url
        else:
            return jsonify({'status': False, 'message': 'Invalid image file'}), 400

    if not update_data:
        return jsonify({'status': False, 'message': 'No updates provided'}), 400

    update_data['timestamp'] = datetime.now(timezone.utc).isoformat()
    doc_ref.update(update_data)

    print("[DEBUG] Journal updated:", update_data)
    return jsonify({'status': True, 'message': 'Journal updated successfully'}), 200



if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")

 
