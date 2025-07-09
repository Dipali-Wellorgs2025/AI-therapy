from flask import Blueprint, request, jsonify
import firebase_admin
from firebase_admin import firestore
import random
import time
import re
import os
from datetime import datetime, timedelta
from twilio.rest import Client

# Create a Blueprint for profile management
profile_bp = Blueprint('profile', __name__)

# Get Firestore client (assumes it's already initialized in main.py)
def get_db():
    return firestore.client()

# Utility function to validate phone number
def validate_phone_number(phone):
    """Validate phone number format (basic validation)"""
    # Remove any spaces, dashes, or parentheses
    phone = re.sub(r'[^\d+]', '', phone)
    
    # Check if it's a valid format (10-15 digits, may start with +)
    if re.match(r'^\+?[\d]{10,15}$', phone):
        return True
    return False

# Utility function to generate OTP
def generate_otp():
    """Generate a 6-digit OTP"""
    return random.randint(100000, 999999)

# Store OTPs temporarily (in production, use Redis or similar)
otp_storage = {}

@profile_bp.route('/editprofile', methods=['POST'])
def edit_profile():
    """
    Edit user profile endpoint
    Query Parameter: userid
    Body: name, nickname, phone_number (all optional)
    """
    try:
        # Get user ID from query parameters or request body
        user_id = request.args.get('userid') or request.args.get('uid')
        
        # Get data from request (supports both JSON and form data)
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict()
        
        # If uid is in the request body, use that
        if not user_id:
            user_id = data.get('uid', '').strip()
            
        if not user_id:
            return jsonify({
                "status": False,
                "message": "User ID is required as query parameter or in request body"
            }), 400

        # Extract profile fields (all optional)
        name = data.get('name', '').strip()
        nickname = data.get('nickname', '').strip()
        # Use 'phone' as the field name
        phone = data.get('phone', '').strip()

        # Validate phone number if provided
        if phone and not validate_phone_number(phone):
            return jsonify({
                "status": False,
                "message": "Invalid phone number format"
            }), 400

        # Get Firestore database
        db = get_db()
        
        # Reference to user document
        user_ref = db.collection("users").document(user_id)
        
        # Check if user exists
        user_doc = user_ref.get()
        if not user_doc.exists:
            # Create new user document if it doesn't exist
            user_data = {
                "uid": user_id,
                "updated_at": datetime.utcnow().isoformat()
            }
        else:
            user_data = user_doc.to_dict()
            user_data["updated_at"] = datetime.utcnow().isoformat()

        # Store old phone number to check if it changed
        old_phone = user_data.get('phone', '')
        phone_changed = False

        # Update fields if provided
        if name:
            user_data["name"] = name
        if nickname:
            user_data["nickname"] = nickname
        if phone:
            user_data["phone"] = phone
            # Check if phone number changed
            if old_phone != phone:
                phone_changed = True

        # Save updated user data
        user_ref.set(user_data)

        response_data = {
            "status": True,
            "message": "User updated successfully"
        }

        # If phone number changed, generate OTP
        if phone_changed and phone:
            try:
                otp_response = generate_otp_for_phone(phone)
                if otp_response["status"]:
                    response_data["otp_generated"] = True
                    response_data["otp_message"] = "OTP sent to new phone number"
                    # In development, include OTP in response (remove in production)
                    response_data["otp"] = otp_response["otp"]
                else:
                    response_data["otp_generated"] = False
                    response_data["otp_message"] = "Failed to generate OTP"
            except Exception as e:
                print(f"OTP generation failed: {e}")
                response_data["otp_generated"] = False
                response_data["otp_message"] = "Failed to generate OTP"

        return jsonify(response_data), 200

    except Exception as e:
        print(f"Error in edit_profile: {e}")
        return jsonify({
            "status": False,
            "message": "An error occurred while updating profile"
        }), 500

@profile_bp.route('/generateotp', methods=['POST'])
def generate_otp_endpoint():
    """
    Generate OTP for phone number verification
    Input: phone_number
    """
    try:
        # Get data from request
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict()

        # Support both 'phone' and 'phone_number' field names
        phone = data.get('phone', '').strip()
        
        if not phone:
            return jsonify({
                "status": False,
                "message": "Phone number is required"
            }), 400

        if not validate_phone_number(phone):
            return jsonify({
                "status": False,
                "message": "Invalid phone number format"
            }), 400

        # Generate OTP
        otp_response = generate_otp_for_phone(phone)
        return jsonify(otp_response), 200 if otp_response["status"] else 400

    except Exception as e:
        print(f"Error in generate_otp_endpoint: {e}")
        return jsonify({
            "status": False,
            "message": "An error occurred while generating OTP"
        }), 500

def generate_otp_for_phone(phone_number):
    """
    Helper function to generate and store OTP for a phone number
    """
    try:
        db = get_db()
        otp = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        otp_data = {
            "otp": str(otp),
            "expires_at": expires_at.isoformat(),
            "attempts": 0
        }
        db.collection("otps").document(phone_number).set(otp_data)
        print(f"Generated OTP {otp} for phone {phone_number}")
        # Here you would send the OTP via SMS
        return {
            "status": True,
            "otp": str(otp)  # In production, don't return OTP in response
        }
    except Exception as e:
        print(f"Error generating OTP: {e}")
        return {
            "status": False,
            "message": "Failed to generate OTP"
        }

@profile_bp.route('/verifyotp', methods=['POST'])
def verify_otp():
    """
    Verify OTP for phone number
    Input: phone_number, otp
    """
    try:
        # Get data from request
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict()

        # Use 'phone' and 'uid' field names
        phone = data.get('phone', '').strip()
        user_otp = data.get('otp', '').strip()
        # Use 'uid' field name
        user_id = data.get('uid', '').strip()

        if not phone or not user_otp:
            return jsonify({
                "status": False,
                "message": "Phone number and OTP are required"
            }), 400

        db = get_db()
        otp_doc = db.collection("otps").document(phone).get()
        if not otp_doc.exists:
            return jsonify({
                "status": False,
                "message": "No OTP found for this phone number"
            }), 400
        otp_data = otp_doc.to_dict()
        # Check if OTP has expired
        expires_at = otp_data.get("expires_at")
        if expires_at:
            expires_at_dt = datetime.fromisoformat(expires_at)
            if datetime.utcnow() > expires_at_dt:
                db.collection("otps").document(phone).delete()
                return jsonify({
                    "status": False,
                    "message": "OTP has expired"
                }), 400
        # Check attempt limit (max 3 attempts)
        attempts = otp_data.get("attempts", 0)
        if attempts >= 3:
            db.collection("otps").document(phone).delete()
            return jsonify({
                "status": False,
                "message": "Maximum OTP attempts exceeded"
            }), 400
        # Verify OTP
        stored_otp = str(otp_data["otp"]).strip()
        input_otp = str(user_otp).strip()
        if stored_otp == input_otp:
            db.collection("otps").document(phone).delete()
            # Update user verification status if user_id provided
            if user_id:
                try:
                    user_ref = db.collection("users").document(user_id)
                    user_ref.update({
                        "updated_at": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    print(f"Error updating user status: {e}")
            return jsonify({
                "status": True,
                "message": "OTP verified successfully"
            }), 200
        else:
            print(f"OTP mismatch: stored='{stored_otp}' input='{input_otp}'")
            db.collection("otps").document(phone).update({"attempts": attempts + 1})
            return jsonify({
                "status": False,
                "message": f"Invalid OTP. {3 - (attempts + 1)} attempts remaining"
            }), 400

    except Exception as e:
        print(f"Error in verify_otp: {e}")
        return jsonify({
            "status": False,
            "message": "An error occurred while verifying OTP"
        }), 500

@profile_bp.route('/getprofile', methods=['GET'])
def get_profile():
    """
    Get user profile
    Query Parameter: userid
    """
    try:
        # Support both 'userid' and 'uid' parameter names
        user_id = request.args.get('userid') or request.args.get('uid')
        if not user_id:
            return jsonify({
                "status": False,
                "message": "User ID is required as query parameter (userid or uid)"
            }), 400

        db = get_db()
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({
                "status": False,
                "message": "User not found"
            }), 404

        user_data = user_doc.to_dict()
        
        # Return simple profile format
        profile_data = {
            "uid": user_data.get("uid"),
            "name": user_data.get("name", ""),
            "nickname": user_data.get("nickname", ""),
            "phone": user_data.get("phone", ""),
            "updated_at": user_data.get("updated_at")
        }

        return jsonify({
            "status": True,
            "data": profile_data
        }), 200

    except Exception as e:
        print(f"Error in get_profile: {e}")
        return jsonify({
            "status": False,
            "message": "An error occurred while fetching profile"
        }), 500

# Utility endpoint to clear expired OTPs (for maintenance)
@profile_bp.route('/cleanup-otps', methods=['POST'])
def cleanup_expired_otps():
    """
    Clean up expired OTPs from memory
    """
    try:
        current_time = time.time()
        expired_phones = [
            phone for phone, data in otp_storage.items()
            if current_time > data["expires_at"]
        ]
        
        for phone in expired_phones:
            del otp_storage[phone]

        return jsonify({
            "status": True,
            "message": f"Cleaned up {len(expired_phones)} expired OTPs"
        }), 200

    except Exception as e:
        print(f"Error in cleanup_expired_otps: {e}")
        return jsonify({
            "status": False,
            "message": "An error occurred while cleaning up OTPs"
        }), 500
