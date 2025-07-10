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

@gratitude_bp.route('/deletegratitude', methods=['DELETE'])
def delete_gratitude():
    gratitude_id = request.args.get('gratitude_id')
    if not gratitude_id:
        return jsonify({'status': False, 'message': 'gratitude_id required'}), 400

    db = firestore.client()
    doc_ref = db.collection('gratitude').document(gratitude_id)
    if not doc_ref.get().exists:
        return jsonify({'status': False, 'message': 'Gratitude entry not found'}), 404

    doc_ref.delete()
    return jsonify({'status': True, 'message': 'Gratitude deleted successfully'}), 200


# 4. Edit gratitude (PUT /editgratitude)

@gratitude_bp.route('/editgratitude', methods=['PUT'])
def edit_gratitude():
    data = request.get_json() or request.form
    userid = data.get('userid')
    gratitude_id = data.get('gratitude_id')
    new_text = data.get('text')

    if not userid or not gratitude_id:
        return jsonify({'status': False, 'message': 'userid and gratitude_id are required'}), 400

    db = firestore.client()
    doc_ref = db.collection('gratitude').document(gratitude_id)
    doc = doc_ref.get()

    if not doc.exists:
        return jsonify({'status': False, 'message': 'Gratitude entry not found'}), 404

    gratitude_data = doc.to_dict()
    if gratitude_data.get('userid') != userid:
        return jsonify({'status': False, 'message': 'Unauthorized: userid mismatch'}), 403

    update_data = {}
    if new_text:
        update_data['text'] = new_text
        update_data['timestamp'] = datetime.utcnow().isoformat()
        doc_ref.update(update_data)
        return jsonify({'status': True, 'message': 'Gratitude updated successfully'}), 200
    else:
        return jsonify({'status': False, 'message': 'No new text provided'}), 400

