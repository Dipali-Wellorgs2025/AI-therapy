from flask import Blueprint, request, jsonify
from firebase_admin import auth
from firebase_config import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup_user():
    data = request.json
    name = data.get('name')
    nickname = data.get('nickname')
    phone = data.get('phone')

    try:
        user = auth.create_user(
            display_name=nickname,
            phone_number=phone,
        )

        # Optional: Save more details to Firestore under 'users'
        db.collection('users').document(user.uid).set({
            'name': name,
            'nickname': nickname,
            'phone': phone
        })

        return jsonify({'message': 'User created', 'uid': user.uid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login_user():
    data = request.json
    phone = data.get('phone')

    try:
        user = auth.get_user_by_phone_number(phone)
        return jsonify({'message': 'User found', 'uid': user.uid}), 200
    except auth.UserNotFoundError:
        return jsonify({'error': 'User not found. Please sign up first.'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
