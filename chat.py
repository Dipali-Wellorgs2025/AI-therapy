from flask import Blueprint, request, jsonify
from firebase_config import db
from datetime import datetime

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/save', methods=['POST'])
def save_chat():
    data = request.json
    chat_data = {
        'uid': data.get('uid'),
        'botName': data.get('botName'),
        'category': data.get('category'),
        'message': data.get('message'),
        'timestamp': datetime.utcnow()
    }

    try:
        db.collection('chats').add(chat_data)
        return jsonify({'message': 'Chat saved'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
