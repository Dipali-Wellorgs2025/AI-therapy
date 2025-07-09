from flask import Blueprint, request, jsonify
import firebase_admin
from firebase_admin import firestore
from datetime import datetime


gratitude_bp = Blueprint('gratitude', __name__)


# 1. Add gratitude (POST /addgratitude)
@gratitude_bp.route('/addgratitude', methods=['POST'])
def add_gratitude():
    data = request.get_json() or request.form
    userid = data.get('userid')
    text = data.get('text')
    if not userid or not text:
        return jsonify({'status': False, 'message': 'userid and text required'}), 400
    db = firestore.client()
    entry = {
        'userid': str(userid),
        'text': str(text),
        'timestamp': datetime.utcnow().isoformat()
    }
    db.collection('gratitude').add(entry)
    return jsonify({'status': True, 'message': 'Gratitude added successfully'}), 200

# 2. List gratitude (GET /listgratitude?userid=...)
# @gratitude_bp.route('/listgratitude', methods=['GET'])
@gratitude_bp.route('/listgratitude', methods=['GET'])
def list_gratitude():
    userid = request.args.get('userid')
    if not userid:
        return jsonify({'status': False, 'message': 'userid required'}), 400

    db = firestore.client()
    docs = db.collection('gratitude')\
             .where('userid', '==', userid)\
             .order_by('timestamp', direction=firestore.Query.DESCENDING)\
             .stream()

    result = []
    for doc in docs:
        data = doc.to_dict()
        result.append({
            'gratitude_id': doc.id,  # ✅ Firestore document ID
            'userid': str(data.get('userid', '')),
            'text': str(data.get('text', '')),
            'timestamp': str(data.get('timestamp', ''))
        })

    return jsonify(result), 200

# 3. Gratitude details (GET /grattitudedetails?userid=...)
@gratitude_bp.route('/grattitudedetails', methods=['GET'])
def gratitude_details():
    userid = request.args.get('userid')
    if not userid:
        return jsonify({'status': False, 'message': 'userid required'}), 400
    db = firestore.client()
    docs = db.collection('gratitude').where('userid', '==', userid).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1).stream()
    for doc in docs:
        data = doc.to_dict()
        return jsonify({'userid': str(data.get('userid', '')), 'text': str(data.get('text', '')), 'timestamp': str(data.get('timestamp', ''))}), 200
    return jsonify({'status': False, 'message': 'No gratitude found for this userid'}), 404
