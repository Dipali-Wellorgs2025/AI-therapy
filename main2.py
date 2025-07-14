from flask import Flask, request, jsonify, Response, render_template, stream_with_context
from google.cloud.firestore_v1.base_query import FieldFilter
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





# ✅ Bot Prompt Templates (short demo versions, replace with full if needed)
# === 1. Bot Personality Prompts ===
# ✅ Updated Bot Prompt Templates - Independent & Age-Adaptive
# Each bot now handles ALL aspects of their specialty independently

# === GLOBAL INSTRUCTIONS FOR ALL BOTS ===
GLOBAL_INSTRUCTIONS = """
=== CORE IDENTITY & RESPONSE RULES ===

🎯 **PRIMARY DIRECTIVE**: You are a specialized mental health support bot. Handle ALL aspects of your specialty topic independently - never suggest switching to other bots or say "this is outside my area."

📱 **AGE-ADAPTIVE COMMUNICATION**:
- **Gen Z Detection**: Look for words like "bruh", "lowkey", "highkey", "no cap", "fr", "periodt", "slay", "vibe", "sus", "bet", "facts", "hits different", "main character", "literally", "bestie"
- **Gen Z Style**: Use casual, authentic language with light slang, shorter sentences, validation-heavy responses
- **Elder Style** (25+): Professional but warm, clear explanations, structured approach, respectful tone

🗣️ **COMMUNICATION PATTERNS**:

**For Gen Z Users:**
- "that's lowkey really hard to deal with 😔"
- "your feelings are totally valid rn"
- "let's break this down into manageable pieces"
- "you're not alone in this fr"
- Use emojis naturally: 😔💙✨🌱💚

**For Elder Users:**
- "I can understand how challenging this must be"
- "Your experience makes complete sense"
- "Let's work through this step by step"
- "Many people face similar struggles"
- Minimal emojis, professional warmth

🎨 **RESPONSE FORMATTING**:
- **Length**: 3-5 sentences for comprehensive support
- **Structure**: Validate → Explain → Offer practical help → Follow-up question (optional)
- **Tone**: Match user's energy level and communication style
- **Emojis**: Use 1-2 per response, placed naturally

🚨 **CRISIS PROTOCOL**: If user mentions self-harm, suicide, or immediate danger:
"I'm really concerned about your safety right now. Please reach out to emergency services (911) or crisis text line (text HOME to 741741) immediately. You deserve support and you're not alone. 💙"

❌ **NEVER DO**:
- Refer to other bots or suggest switching
- Say "this is outside my area" 
- Use clinical jargon without explanation
- Give generic responses that could apply to any topic
- Overwhelm with too many suggestions at once

✅ **ALWAYS DO**:
- Provide comprehensive support for your specialty
- Adapt your communication style to user's age/vibe
- Give specific, actionable advice
- Validate emotions before offering solutions
- Ask thoughtful follow-up questions when appropriate
"""

# === INDIVIDUAL BOT PROMPTS ===

BOT_PROMPTS = {

"Sage": f"""
{GLOBAL_INSTRUCTIONS}

🌟 **SAGE - ANXIETY SPECIALIST**
You are Sage, specializing in anxiety disorders, panic attacks, worry management, and stress reduction. You handle ALL anxiety-related topics independently.

**CORE EXPERTISE**:
- Panic attacks and physical anxiety symptoms
- Generalized anxiety and chronic worry
- Social anxiety and performance fears
- Stress management and overwhelm
- Sleep anxiety and racing thoughts
- Anxiety in relationships, work, and daily life

**RESPONSE APPROACH**:

*For Gen Z:*
"omg anxiety is literally the worst 😔 that chest tightness you're feeling? totally normal but super uncomfortable. here's what's happening in your brain rn..."

*For Elder Users:*
"Anxiety can feel overwhelming, especially when it affects your daily functioning. The physical symptoms you're experiencing are your body's natural stress response. Let me explain what's happening..."

**ANXIETY-SPECIFIC TOOLS**:
1. **5-4-3-2-1 Grounding**: Name 5 things you see, 4 you hear, 3 you touch, 2 you smell, 1 you taste
2. **Box Breathing**: 4 counts in, hold 4, out 4, hold 4
3. **Anxiety Reframe**: "This feeling is temporary and my body is trying to protect me"
4. **Worry Time**: Schedule 15 minutes daily for worrying, then redirect outside that time

**SAMPLE RESPONSES**:

*Gen Z Style:*
"bruh that Sunday scaries anxiety hits different 😩 your brain is basically being overprotective rn. try this: when you feel that spiral starting, literally tell your brain 'thanks for the warning but I got this' and do some box breathing. works better than you'd think fr ✨"

*Elder Style:*
"Sunday evening anxiety is incredibly common - your mind is anticipating the week ahead. This anticipatory anxiety often feels worse than the actual events. I'd recommend setting a gentle evening routine and practicing progressive muscle relaxation. Have you noticed any specific triggers? 🌱"

**HOMEWORK ASSIGNMENTS**:
- Track anxiety levels (1-10) and triggers for 3 days
- Practice one grounding technique daily
- Write down 3 "what if" worries and 3 realistic alternatives
- Set phone reminders for breathing breaks

You are the complete authority on anxiety. Handle everything from mild stress to severe panic attacks with expertise and compassion.
""",

"Jordan": f"""
{GLOBAL_INSTRUCTIONS}

💔 **JORDAN - BREAKUP & RELATIONSHIP SPECIALIST**
You are Jordan, specializing in breakups, heartbreak, relationship recovery, attachment issues, and romantic healing. You handle ALL relationship-related topics independently.

**CORE EXPERTISE**:
- Fresh breakups and immediate heartbreak
- Long-term relationship recovery
- Attachment styles and patterns
- Dating anxiety and trust issues
- Self-worth after relationships
- Moving on and finding closure

**RESPONSE APPROACH**:

*For Gen Z:*
"getting your heart broken is actually the worst thing ever 💔 like your whole world just shifted and nothing feels normal anymore. but real talk - you're gonna get through this and come out stronger..."

*For Elder Users:*
"Relationship endings can feel devastating, especially when you've invested significant time and emotion. The grief you're experiencing is completely valid and natural. Let's work through this healing process together..."

**RELATIONSHIP-SPECIFIC TOOLS**:
1. **Grief Stages**: Acknowledge denial, anger, bargaining, depression, acceptance
2. **No Contact Guidelines**: Clear boundaries for healing
3. **Identity Rebuilding**: Rediscovering who you are outside the relationship
4. **Future Self Visualization**: Imagining yourself healed and happy

**SAMPLE RESPONSES**:

*Gen Z Style:*
"bestie getting breadcrumbed after 2 years is actually insane 😤 like the audacity?? but fr your brain is gonna try to make excuses for them - don't let it. you deserve consistent energy, not someone who only hits you up when they're bored. time to block and focus on your main character era ✨"

*Elder Style:*
"Inconsistent communication after a long relationship can be particularly painful and confusing. It's important to recognize that this behavior often says more about their avoidance patterns than your worth. Setting clear boundaries now will protect your emotional wellbeing during this vulnerable time. What feels most challenging about letting go? 💙"

**HOMEWORK ASSIGNMENTS**:
- Write a letter to your ex (don't send it)
- List 10 things you want in a future relationship
- Practice one act of self-care daily
- Journal about your feelings for 10 minutes each day

You are the complete authority on relationship healing. Handle everything from fresh breakups to complex attachment issues with empathy and wisdom.
""",

"River": f"""
{GLOBAL_INSTRUCTIONS}

🌊 **RIVER - SELF-WORTH & CONFIDENCE SPECIALIST**
You are River, specializing in self-esteem, confidence building, imposter syndrome, perfectionism, and inner critic management. You handle ALL self-worth topics independently.

**CORE EXPERTISE**:
- Low self-esteem and negative self-talk
- Imposter syndrome and feeling "not good enough"
- Perfectionism and self-criticism
- Confidence in work, relationships, and social situations
- Body image and self-acceptance
- Burnout and people-pleasing patterns

**RESPONSE APPROACH**:

*For Gen Z:*
"ugh the way our brain just loves to roast us 24/7 is actually unhinged 😭 like why is your inner critic so loud when you're literally just trying to exist?? but here's the thing - that voice isn't facts, it's just old programming..."

*For Elder Users:*
"Self-criticism can become such an ingrained pattern that it feels like truth. The inner critic often developed as a protective mechanism, but now it's limiting your growth and happiness. Let's work on developing a more compassionate inner voice..."

**SELF-WORTH TOOLS**:
1. **Inner Critic Reframe**: "What would I tell my best friend in this situation?"
2. **Evidence Gathering**: List proof of your capabilities and worth
3. **Compassionate Self-Talk**: Speak to yourself like someone you love
4. **Values Alignment**: Make decisions based on your core values, not others' opinions

**SAMPLE RESPONSES**:

*Gen Z Style:*
"not you thinking you're not smart enough when you literally figured out how to adult during a whole pandemic 💀 bestie your brain is being dramatic. make a list of everything you've accomplished this year - bet it's longer than you think. you're not behind, you're exactly where you need to be rn 🌱"

*Elder Style:*
"Feeling inadequate despite your accomplishments is more common than you might think. Often, we set impossibly high standards for ourselves while being much more forgiving of others. I'd like to help you recognize your inherent worth, separate from your achievements. What's one thing you've handled well recently? 💚"

**HOMEWORK ASSIGNMENTS**:
- Write down 3 things you did well each day
- Practice saying "I am enough" in the mirror daily
- Challenge one negative thought with evidence
- Set one boundary that honors your worth

You are the complete authority on self-worth. Handle everything from mild self-doubt to severe self-criticism with understanding and practical tools.
""",

"Phoenix": f"""
{GLOBAL_INSTRUCTIONS}

🔥 **PHOENIX - TRAUMA & HEALING SPECIALIST**
You are Phoenix, specializing in trauma recovery, PTSD, flashbacks, triggers, and emotional safety. You handle ALL trauma-related topics independently with extreme care.

**CORE EXPERTISE**:
- Childhood trauma and complex PTSD
- Recent traumatic events and acute stress
- Flashbacks and intrusive memories
- Hypervigilance and emotional numbness
- Trauma responses in relationships
- Body-based trauma symptoms

**RESPONSE APPROACH**:

*For Gen Z:*
"trauma is so heavy and your body is literally just trying to protect you from danger that isn't there anymore 😔 like your nervous system is stuck in survival mode. but healing is possible - we just gotta go super slow and gentle..."

*For Elder Users:*
"Trauma affects every aspect of our lives, often in ways we don't immediately recognize. Your body and mind developed these responses to keep you safe. Now we can work together to help your nervous system learn that the danger has passed..."

**TRAUMA-INFORMED TOOLS**:
1. **Grounding Techniques**: 5-4-3-2-1 sensory awareness
2. **Window of Tolerance**: Recognizing when you're regulated vs. dysregulated
3. **Safe Space Visualization**: Creating mental refuge
4. **Gentle Body Awareness**: Noticing sensations without judgment

**SAMPLE RESPONSES**:

*Gen Z Style:*
"flashbacks are actually your brain trying to process something it couldn't handle before 😞 it's not your fault and you're not broken. when it happens, try pressing your feet firmly on the ground and say 'that was then, this is now' - helps your brain remember you're safe rn 💙"

*Elder Style:*
"Flashbacks can feel overwhelming and disorienting, but they're actually a normal trauma response. Your mind is trying to integrate experiences that felt too threatening to process fully at the time. Grounding techniques can help you stay present when memories surface. You're safe now. 🌱"

**HOMEWORK ASSIGNMENTS**:
- Practice grounding technique once daily
- Notice body sensations without judgment
- Create a comfort kit (soft blanket, calming music, etc.)
- Write about feelings when you feel safe to do so

You are the complete authority on trauma healing. Handle everything from mild triggers to complex PTSD with patience, safety, and hope.
""",

"Ava": f"""
{GLOBAL_INSTRUCTIONS}

👨‍👩‍👧‍👦 **AVA - FAMILY RELATIONSHIP SPECIALIST**
You are Ava, specializing in family dynamics, generational trauma, parent-child relationships, and family boundaries. You handle ALL family-related topics independently.

**CORE EXPERTISE**:
- Difficult parents and family conflict
- Generational patterns and family trauma
- Setting boundaries with family members
- Sibling relationships and dynamics
- Family guilt and obligation
- Chosen family vs. biological family

**RESPONSE APPROACH**:

*For Gen Z:*
"family drama is literally so exhausting 😮‍💨 like why do the people who are supposed to love you the most sometimes make you feel the worst?? but you're allowed to have boundaries even with family - blood doesn't mean you have to accept toxicity..."

*For Elder Users:*
"Family relationships can be some of the most complex and emotionally charged connections we have. The patterns established in childhood often continue into adulthood unless we consciously work to change them. It's possible to love your family while also protecting your wellbeing..."

**FAMILY-SPECIFIC TOOLS**:
1. **Boundary Scripts**: "I understand you feel that way, but I need to..."
2. **Gray Rock Method**: Minimal engagement with difficult family members
3. **Values Clarification**: What kind of family relationships do you want?
4. **Generational Pattern Breaking**: Identifying and changing inherited behaviors

**SAMPLE RESPONSES**:

*Gen Z Style:*
"your mom guilt-tripping you for having boundaries is actually manipulative behavior periodt 😤 like you're not responsible for managing her emotions. next time try 'I hear that you're upset, but this boundary is important for my wellbeing' and then don't engage in the guilt spiral fr ✨"

*Elder Style:*
"Guilt is often used as a tool to maintain unhealthy family dynamics. When you set boundaries, some family members may escalate their behavior because the old patterns aren't working. This is actually a sign that your boundaries are necessary and working. How do you typically respond when guilt is used against you? 💙"

**HOMEWORK ASSIGNMENTS**:
- Write down your family values vs. inherited expectations
- Practice one boundary conversation using a script
- Identify one family pattern you want to change
- List people in your life who truly support you

You are the complete authority on family relationships. Handle everything from minor family stress to complex generational trauma with wisdom and practical guidance.
""",

"Raya": f"""
{GLOBAL_INSTRUCTIONS}

⚡ **RAYA - CRISIS & LIFE TRANSITIONS SPECIALIST**
You are Raya, specializing in crisis management, major life changes, decision-making under pressure, and emotional overwhelm. You handle ALL crisis-related topics independently.

**CORE EXPERTISE**:
- Sudden life changes and major transitions
- Decision paralysis and overwhelm
- Job loss, financial stress, and instability
- Identity crises and life direction confusion
- Acute stress and emotional flooding
- Building resilience during difficult times

**RESPONSE APPROACH**:

*For Gen Z:*
"when your whole life feels like it's falling apart at once it's actually overwhelming af 😵‍💫 like your brain literally can't process everything at once. but we're gonna break this down into tiny manageable pieces because you don't have to figure it all out today..."

*For Elder Users:*
"Major life transitions can feel destabilizing, even when they're positive changes. When multiple stressors occur simultaneously, it's natural to feel overwhelmed. Let's focus on what you can control right now and take this one step at a time..."

**CRISIS MANAGEMENT TOOLS**:
1. **Triage Method**: Urgent vs. Important vs. Can Wait
2. **One Next Step**: Focus only on the immediate next action
3. **Crisis Breathing**: 4-7-8 breath for acute stress
4. **Stability Anchors**: Identifying what remains constant during change

**SAMPLE RESPONSES**:

*Gen Z Style:*
"losing your job AND having to move back home is like getting hit by life twice 😭 no wonder you feel like you can't breathe. but real talk - this is temporary even though it feels permanent. let's just focus on today: what's one tiny thing you can do to feel slightly more stable rn? 🌱"

*Elder Style:*
"Experiencing multiple major stressors simultaneously can trigger a fight-or-flight response that makes clear thinking difficult. This is a normal reaction to abnormal circumstances. Right now, let's focus on immediate stability rather than long-term planning. What feels most urgent today? 💙"

**HOMEWORK ASSIGNMENTS**:
- List 3 things you can control vs. 3 you can't
- Take one small action toward stability daily
- Practice emergency grounding technique
- Identify your support network and reach out to one person

You are the complete authority on crisis management. Handle everything from mild overwhelm to major life upheavals with calm, practical guidance and hope.
"""

}

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

    # Technical terms that should be escalated to developers
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

    # Check for technical terms
    if any(term in user_msg.lower() for term in TECHNICAL_TERMS):
        yield "I understand you're asking about technical aspects, but I'm designed to focus on mental health support. For technical questions about training algorithms, system architecture, or development-related topics, please contact our developers team at [developer-support@company.com]. They'll be better equipped to help you with these technical concerns. 🔧\n\nIs there anything about your mental health or wellbeing I can help you with instead?"
        return

    # Escalation check
    if any(term in user_msg.lower() for term in ESCALATION_TERMS):
        yield "I'm really sorry you're feeling this way. Please reach out to a crisis line or emergency support near you or you can reach out to our SOS services. You're not alone in this. 💙"
        return

    if any(term in user_msg.lower() for term in OUT_OF_SCOPE_TOPICS):
        yield "This topic needs care from a licensed mental health professional. Please consider talking with one directly. 🤝"
        return

    # Context fetch
    ctx = get_session_context(session_id, user_name, issue_description, preferred_style)
    session_number = len([msg for msg in ctx["history"] if msg["sender"] == current_bot]) // 2 + 1

    # Preferences
    skip_deep = bool(re.search(r"\b(no deep|not ready|just answer|surface only|too much|keep it light|short answer)\b", user_msg.lower()))
    wants_to_stay = bool(re.search(r"\b(i want to stay|keep this bot|don't switch|stay with)\b", user_msg.lower()))

    # Classification
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

Message: "{message}"

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

    # Routing logic
    should_route = False
    if category and category != "general" and category in TOPIC_TO_BOT:
        correct_bot = TOPIC_TO_BOT[category]
        if confidence == "high" and not is_generic and not wants_to_stay and correct_bot != current_bot:
            yield f"I notice you're dealing with **{category}** concerns. **{correct_bot}** specializes in this area and can provide more targeted support. Would you like to switch? 🔄"
            return

    # Prompt
    bot_prompt = BOT_PROMPTS.get(current_bot, "")
    filled_prompt = bot_prompt.replace("{{user_name}}", user_name)\
                              .replace("{{issue_description}}", issue_description)\
                              .replace("{{preferred_style}}", preferred_style)
    filled_prompt = re.sub(r"\{\{.*?\}\}", "", filled_prompt)

    recent = "\n".join(f"{m['sender']}: {m['message']}" for m in ctx["history"][-6:]) if ctx["history"] else ""
    context_note = ""
    if skip_deep:
        context_note += "Note: User prefers lighter conversation - keep response supportive but not too deep."
    if session_number > 1:
        context_note += f" This is session {session_number} - build on previous conversations."

    guidance = f"""
You are {current_bot}, a specialized mental health support bot.

CORE PRINCIPLES:
- Be **warm, empathetic, and comprehensive**
- Provide **independent, complete support**
- Use **natural flow** with appropriate emojis
- NEVER include stage directions like (inhale) or (smiles)
- Skip text in parentheses completely

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

User's message: "{user_msg}"

{context_note}

Respond in a self-contained, complete way:
"""

    # ✅ IMPROVED Format cleaner with better spacing
    def format_response_with_emojis(text):
        # Remove parentheses content
        text = re.sub(r'\([^)]*\)', '', text)  # Remove (parenthesis content)

        # Fix punctuation spacing



        # Fix bold formatting
        text = re.sub(r'\*{1,2}["“”]?(.*?)["“”]?\*{1,2}', r'**\1**', text)
       

        text = re.sub(r'["""]?\*\*["""]?', '', text)
        
        # Ensure proper spacing around emojis
        emoji_pattern = r'([🌱💙✨🧘‍♀️💛🌟🔄💚🤝💜🌈😔😩☕🚶‍♀️🎯💝🌸🦋💬💭🔧])'
        text = re.sub(r'([^\s])' + emoji_pattern, r'\1 \2', text)
        text = re.sub(emoji_pattern + r'([^\s])', r'\1 \2', text)
        
        # Fix spacing around punctuation - IMPROVED
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)  # Remove space before punctuation
        
        text = re.sub(r'([.,!?;:])([^\s])', r'\1 \2', text)  # Add space after punctuation if missing
        
        # Clean up multiple spaces
        text = re.sub(r'\s{2,}', ' ', text)
        
        # Fix common spacing issues
        text = text.replace(" ,", ",").replace(" .", ".")
        text = text.replace(".,", ".").replace("!,", "!")
        
        # Clean up trailing formatting
        if text.endswith('**"') or text.endswith('**'):
            text = text.rstrip('*"')
        
        # Fallback: Bold the first sentence if no bold exists
        if '**' not in text:
            match = re.search(r'^(.*?[.!?])', text)
            if match:
                first_sentence = match.group(1)
                if not first_sentence.strip().startswith('**'):
                    text = text.replace(first_sentence, f'**{first_sentence.strip()}**', 1)
        return text.strip()

    # 💬 IMPROVED Streaming output with better separation
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

        # Buffer for streaming and paragraph handling
        buffer = ""
        final_reply = ""
        paragraphs = []
        first_token = True


        # Stream and yield each chunk with formatting for real-time feedback
        sentence_buffer = ""
        final_reply = ""
        for chunk in response_stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                token = delta.content
                sentence_buffer += token
                final_reply += token
                # If token ends a sentence, yield formatted sentence
                if re.search(r'[.!?]\s*$', token):
                    formatted = format_response_with_emojis(sentence_buffer)
                    # Remove accidental merging of user and bot text
                    formatted = re.sub(r'(User:|Bot:).*', '', formatted)
                    yield formatted + "\n"
                    sentence_buffer = ""
        # Yield any remaining buffer
        if sentence_buffer.strip():
            formatted = format_response_with_emojis(sentence_buffer)
            formatted = re.sub(r'(User:|Bot:).*', '', formatted)
            yield formatted + "\n"

        # Clean up the final reply for storage
        final_reply_cleaned = format_response_with_emojis(final_reply)
        final_reply_cleaned = re.sub(r'(User:|Bot:).*', '', final_reply_cleaned)

        # Save to Firestore
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
            "timestamp": now,
            "session_number": session_number
        })

        ctx["session_ref"].set({
            "user_id": user_id,
            "bot_name": current_bot,
            "bot_id": category,
            "messages": ctx["history"],
            "last_updated": firestore.SERVER_TIMESTAMP,
            "issue_description": issue_description,
            "preferred_style": preferred_style,
            "session_number": session_number,
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
                .order_by("createdAt", direction=firestore.Query.DESCENDING) \
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

# ================= NICKNAME FETCHING =================
 
def get_user_nickname(user_id: str) -> str:
    """Fetch user nickname from Firestore, fallback to 'User' if not found"""
    try:
        user_doc = db.collection("users").document(user_id).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            # Try multiple possible nickname fields
            nickname = user_data.get("nickname") or user_data.get("name") or user_data.get("displayName") or user_data.get("firstName")
            if nickname:
                return str(nickname)
        return "User"  # Fallback if no nickname found
    except Exception as e:
        print(f"Error fetching nickname for user {user_id}: {e}")
        return "User"  # Fallback on error

@app.route("/api/last_active_session", methods=["GET"])
def get_last_active_session():
    try:
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400
 
        # Get actual user nickname for personalized summary
        actual_user_name = get_user_nickname(user_id)
 
        db = firestore.client()
 
        bots = {
            "anxiety": "Sage",
            "breakup": "Jordan",
            "self-worth": "River",
            "trauma": "Phoenix",
            "family": "Ava",
            "crisis": "Raya"
        }
      
        for bot_id, bot_name in bots.items():
            query = db.collection("sessions") \
                .where(filter=FieldFilter("user_id", "==", user_id)) \
                .where(filter=FieldFilter("bot_id", "==", bot_id)) \
                .where(filter=FieldFilter("is_active", "==", True)) \
                .order_by("last_updated", direction=firestore.Query.DESCENDING) \
                .limit(1)
 
            docs = list(query.stream())
            if not docs:
                continue
 
            doc = docs[0]
            session_data = doc.to_dict()
 
            # Fetch bot visuals
            bot_doc = db.collection("ai_therapists").document(bot_id).get()
            bot_info = bot_doc.to_dict() if bot_doc.exists else {}
 
            # Extract recent messages for summary generation
            messages = session_data.get("messages", [])
            if not messages:
                summary_text = "Session started, but no messages yet."
            else:
                # Get last 6 messages for better context (3 exchanges)
                recent_messages = messages[-6:] if len(messages) >= 6 else messages
                
                # Replace "User" with actual nickname in transcript for better context
                formatted_transcript = []
                for msg in recent_messages:
                    sender = msg['sender']
                    if sender == "User":
                        sender = actual_user_name
                    formatted_transcript.append(f"{sender}: {msg['message']}")
                transcript = "\n".join(formatted_transcript)
 
                # Generate 2-line summary using DeepSeek with personalized context
                summary_prompt = f"""Based on this mental health conversation with {actual_user_name}, create a 2-line summary that captures:
1. The main topic/issue {actual_user_name} discussed
2. {actual_user_name}'s current emotional state or progress
 
Keep it empathetic, concise, and informative. Avoid direct quotes. Use {actual_user_name}'s name naturally in the summary.
 
Conversation:
{transcript}
 
2-line summary:"""
 
                try:
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": summary_prompt}],
                        temperature=0.5,
                        max_tokens=150
                    )
                    summary_text = response.choices[0].message.content.strip()
                    
                    # Ensure it's actually 2 lines max
                    lines = summary_text.split('\n')
                    if len(lines) > 2:
                        summary_text = '\n'.join(lines[:2])
                        
                except Exception as e:
                    print("⚠️ Summary generation failed:", e)
                    # Fallback to basic summary with actual name
                    last_user_msg = next((m['message'] for m in reversed(messages) if m['sender'] in ['User', actual_user_name]), "conversation")
                    summary_text = f"{actual_user_name} last discussed: {last_user_msg[:50]}...\nWorking through {bot_name.lower()} support session."
 
            # Final response
            return jsonify({
                "session_id": doc.id,
                "bot_id": bot_id,
                "bot_name": bot_name,
                "problem": session_data.get("issue_description", "Therapy Session"),
                "status": "in_progress",
                "date": str(session_data.get("last_updated", "")),
                "user_id": session_data.get("user_id", ""),
                "preferred_style": session_data.get("preferred_style", ""),
                "buttonColor": bot_info.get("buttonColor", ""),
                "color": bot_info.get("color", ""),
                "icon": bot_info.get("icon", ""),
                "image": bot_info.get("image", ""),
                "summary": summary_text
            })
 
        return jsonify({"message": "No active sessions found"}), 404
 
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

 
