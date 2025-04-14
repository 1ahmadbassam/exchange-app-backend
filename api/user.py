from flask import Blueprint, jsonify, request
from password_strength import PasswordPolicy, PasswordStats
from password_strength.tests import Uppercase, Length, Numbers, Special, Strength, EntropyBits
from email_validator import validate_email, EmailNotValidError

from init import limiter, db, bcrypt
from model.user import User, UserSchema
from util.token import create_token
from util.user import USER_FORBIDDEN_CHARACTERS, PASSWORD_FORBIDDEN_CHARACTERS

policy = PasswordPolicy.from_names(
    length=12,
    uppercase=2,
    numbers=2,
    special=1,
    strength=0.4,
    entropybits=70  # 70 bits of entropy is a fair compromise between alphabetical, numeric, and ASCII characters
)


def test_password(password):
    tests = policy.test(password)
    hh = []
    for test in tests:
        if type(test) == Length:
            hh.append("Password must be at least " + str(test.length) + " characters long.")
        elif type(test) == Uppercase:
            hh.append(str(test.count) + " uppercase characters required.")
        elif type(test) == Numbers:
            hh.append(str(test.count) + " numbers required.")
        elif type(test) == Special:
            hh.append(str(test.count) + " symbols required (any of ~!@#$%^&*()_+).")
        elif type(test) == Strength:
            hh.append("Password too weak.")
        elif type(test) == EntropyBits:
            hh.append("Password does not have enough variability.")
    return hh


user_bp = Blueprint('user', __name__)
user_schema = UserSchema()


@user_bp.route('/user', methods=['POST'])
@limiter.limit("10 per minute")
def create_user():
    user_name = request.json.get('user_name', '').strip()
    email = request.json.get('email', '').strip()
    password = request.json.get('password', '').strip()

    if not user_name or not password or not email:
        return jsonify({"error": "Missing required fields"}), 400

    for char in USER_FORBIDDEN_CHARACTERS:
        if char in user_name:
            return jsonify({"error": "Forbidden character in username '" + char + "'"}), 400

    for char in PASSWORD_FORBIDDEN_CHARACTERS:
        if char in password:
            return jsonify({"error": "Forbidden character in password '" + char + "'"}), 400

    if db.session.execute(db.select(User).filter_by(user_name=user_name)).scalar():
        return jsonify({"error": "User already exists"}), 400
    if len(user_name) > 30:
        return jsonify({"error": "Username too long"}), 400

    # check if email is valid
    try:
        validated_email = validate_email(email)
    except EmailNotValidError as e:
        return jsonify({"error": "Email not valid: " + str(e)}), 400

    email = validated_email.normalized

    if db.session.execute(db.select(User).filter_by(email=email)).scalar():
        return jsonify({"error": "Email already registered"}), 400

    # check if password meets complexity requirements
    test = test_password(password)
    if test:
        return jsonify({"error": "Invalid password",
                        "tests": test}), 403

    user = User(user_name=user_name, password=password, email=email)
    db.session.add(user)
    db.session.commit()
    return jsonify(user_schema.dump(user)), 200


@user_bp.route('/authentication', methods=['POST'])
@limiter.limit("10 per minute")
def authenticate_user():
    user_name = request.json.get('user_name', '').strip()
    password = request.json.get('password', '').strip()

    if not user_name or not password:
        return jsonify({"error": "Missing required fields"}), 400

    user = db.session.execute(db.select(User).filter_by(user_name=user_name)).scalar()

    if not user or not bcrypt.check_password_hash(user.hashed_password, password):
        return jsonify({"error": "Invalid or expired token"}), 403

    token = create_token(user.id)
    return jsonify({"token": token}), 200


@user_bp.route('/password-strength', methods=['POST'])
@limiter.limit("10 per minute")
def check_password_strength():
    password = str(request.json.get('password', '')).strip()
    if not password:
        return jsonify({"error": "Missing required fields"}), 400
    s = PasswordStats(password).strength()
    return jsonify({
        "strength_score": s,
        "classification": "Weak" if s <= 0.4 else "Moderate" if s <= 0.8 else "Strong"
    }), 200
