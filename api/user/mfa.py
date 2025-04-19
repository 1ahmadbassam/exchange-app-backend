from flask import jsonify, request, Blueprint

from init import limiter, db
from model.user import UserSchema
from util.token import get_b64encoded_qr_image
from util.user import validate_token

user_mfa_bp = Blueprint('user_mfa', __name__, url_prefix='/mfa')
user_schema = UserSchema()


@user_mfa_bp.route('/register', methods=['GET'])
@limiter.limit("10 per minute")
def get_mfa():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    if user.mfa:
        return jsonify({"error": "MFA already enabled"}), 400
    uri = user.get_authentication_setup_uri()
    return jsonify({"user": user_schema.dump(user), "uri": uri, "qr": get_b64encoded_qr_image(uri)}), 200


@user_mfa_bp.route('/register', methods=['POST'])
@limiter.limit("10 per minute")
def register_mfa():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    otp = str(request.json.get('otp', '')).strip()
    if not otp or not user.is_otp_valid(otp):
        return jsonify({"error": "Invalid OTP"}), 403
    user.mfa = True
    db.session.commit()
    return '', 200


@user_mfa_bp.route('/refresh', methods=['POST'])
@limiter.limit("10 per minute")
def refresh_mfa():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    if not user.mfa:
        return jsonify({"error": "MFA not enabled"}), 400
    otp = str(request.json.get('otp', '')).strip()
    if not otp or not user.is_otp_valid(otp):
        return jsonify({"error": "Invalid OTP"}), 403
    return '', 200


@user_mfa_bp.route('/remove', methods=['POST'])
@limiter.limit("10 per minute")
def remove_mfa():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    if not user.mfa:
        return jsonify({"error": "MFA not enabled"}), 400
    otp = str(request.json.get('otp', '')).strip()
    if not otp or not user.is_otp_valid(otp):
        return jsonify({"error": "Invalid OTP"}), 403
    user.disable_mfa()
    db.session.commit()
    return '', 200
