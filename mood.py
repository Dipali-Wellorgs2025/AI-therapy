from flask import Blueprint, request, jsonify
from firebase_config import db
from datetime import datetime

mood_bp = Blueprint('mood', __name__)

@mood_bp.route('/save', methods=['POST'])
def save_mood():
    data = request.json
    mood_data = {
        'uid': data.get('uid'),
        'mood': data.get('mood'),
        'intensity': data.get('intensity'),
        'emoji': data.get('emoji'),
        'note': data.get('note', ''),
        'timestamp': datetime.utcnow()
    }

    try:
        db.collection('moods').add(mood_data)
        return jsonify({'message': 'Mood saved'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
