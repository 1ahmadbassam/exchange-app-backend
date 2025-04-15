from email_validator import validate_email, EmailNotValidError
from flask import Blueprint, jsonify, request, url_for, render_template
from password_strength import PasswordPolicy, PasswordStats
from password_strength.tests import Uppercase, Length, Numbers, Special, Strength, EntropyBits

from init import limiter, db, bcrypt
from model.user import User, UserSchema, UnconfirmedUser
from util.mail import send_email
from util.token import create_jwt, confirm_verification_token, generate_verification_token
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

    if (db.session.execute(db.select(User).filter_by(user_name=user_name)).scalar()
            or db.session.execute(db.select(UnconfirmedUser).filter_by(user_name=user_name)).scalar()):
        return jsonify({"error": "User already exists"}), 400
    if len(user_name) > 30:
        return jsonify({"error": "Username too long"}), 400

    # check if email is valid
    try:
        validated_email = validate_email(email)
    except EmailNotValidError as e:
        return jsonify({"error": "Email not valid: " + str(e)}), 400

    email = validated_email.normalized

    if (db.session.execute(db.select(User).filter_by(email=email)).scalar()
            or (db.session.execute(db.select(UnconfirmedUser).filter_by(email=email)).scalar())):
        return jsonify({"error": "Email already registered"}), 400

    # check if password meets complexity requirements
    test = test_password(password)
    if test:
        return jsonify({"error": "Invalid password",
                        "tests": test}), 403

    user = UnconfirmedUser(user_name=user_name, password=password, email=email)
    db.session.add(user)
    db.session.commit()

    # generate and send verification token
    token = generate_verification_token(email)
    confirm_url = url_for("user.verify_user", token=token, _external=True)
    html = render_template("verify_mail.html", confirm_url=confirm_url)
    subject = "LBP Exchange Tracker - Confirm your email"
    send_email(user.email, subject, html)

    return jsonify({"error": "Email verification required"}), 401


@user_bp.route("/verify", methods=['POST'])
@limiter.limit("10 per minute")
def resend_verify_user():
    email = request.json.get('email', '').strip()
    if not email:
        return jsonify({"error": "Missing required fields"}), 400

    # check if email is valid
    try:
        validated_email = validate_email(email)
    except EmailNotValidError as e:
        return jsonify({"error": "Email not valid: " + str(e)}), 400

    email = validated_email.normalized

    u_user = db.query(UnconfirmedUser).filter_by(email=email).scalar()
    if not u_user:
        if db.session.query(User).filter_by(user_name=email).scalar():
            return jsonify({"error": "Email already verified"}), 400
        else:
            return jsonify({"error": "Email not valid"}), 403

    # generate and send verification token
    token = generate_verification_token(email)
    confirm_url = url_for("user.verify_user", token=token, _external=True)
    html = render_template("verify_mail.html", confirm_url=confirm_url)
    subject = "LBP Exchange Tracker - Confirm your email"
    send_email(email, subject, html)

    return jsonify({"error": "Email verification required"}), 401


@user_bp.route("/verify/<token>", methods=['GET'])
@limiter.limit("10 per minute")
def verify_user(token):
    valid, email = confirm_verification_token(token)
    if not valid:
        return render_template("verify_error.html", error_message=email), 403
    u_user = db.session.query(UnconfirmedUser).filter_by(email=email).scalar()
    if not u_user:
        if db.session.query(User).filter_by(user_name=email).scalar():
            return render_template("verify_error.html", error_message="Email already verified"), 400
        else:
            return render_template("verify_error.html", error_message="Email not valid"), 403
    user = User(user_name=u_user.user_name, password=u_user.hashed_password, email=email, hsh=False)
    db.session.add(user)
    db.session.delete(u_user)
    db.session.commit()
    return render_template("verify.html"), 200


@user_bp.route("/reset", methods=['POST'])
@limiter.limit("10 per minute")
def password_reset_request():
    email = request.json.get('email', '').strip()
    if not email:
        return jsonify({"error": "Missing required fields"}), 400

    # check if email is valid
    try:
        validated_email = validate_email(email)
    except EmailNotValidError as e:
        return jsonify({"error": "Email not valid: " + str(e)}), 400

    email = validated_email.normalized

    user = db.session.query(User).filter_by(email=email).scalar()
    if not user:
        user = db.session.query(UnconfirmedUser).filter_by(email=email).scalar()
        if not user:
            return jsonify({"error": "Email not valid"}), 403
    if not user.can_change_password():
        return jsonify({"error": "Password changed recently. Please wait at least one hour since you last changed your password."}), 400

    # generate and send verification token
    token = generate_verification_token(email)
    confirm_url = url_for("user.password_reset_form", token=token, _external=True)
    html = render_template("reset_mail.html", confirm_url=confirm_url)
    subject = "LBP Exchange Tracker - Reset your password"
    send_email(email, subject, html)
    return '', 200


@user_bp.route("/reset/<token>", methods=['GET'])
@limiter.limit("10 per minute")
def password_reset_form(token):
    valid, email = confirm_verification_token(token, expiration=3600)
    if not valid:
        return render_template("reset_error.html", error_message=email), 403
    user = db.session.query(User).filter_by(email=email).scalar()
    if not user:
        user = db.session.query(UnconfirmedUser).filter_by(email=email).scalar()
        if not user:
            return render_template("reset_error.html", error_message="Email not valid"), 403
    return render_template("reset.html", reset_url=url_for("user.password_reset", token=token, _external=True)), 200


@user_bp.route("/reset/<token>", methods=['POST'])
@limiter.limit("10 per minute")
def password_reset(token):
    valid, email = confirm_verification_token(token, expiration=3600)
    if not valid:
        return jsonify({"error": email}), 400
    user = db.session.query(User).filter_by(email=email).scalar()
    if not user:
        user = db.session.query(UnconfirmedUser).filter_by(email=email).scalar()
        if not user:
            return jsonify({"error": "Email not valid"}), 403

    if not user.can_change_password():
        return jsonify({"error": "Password changed recently. Please wait at least one hour since you last changed your password."}), 400

    password = request.json.get('password', '').strip()
    if not password:
        return jsonify({"error": "New password is required"}), 400

    if bcrypt.check_password_hash(user.hashed_password, password):
        return jsonify({"error": "Cannot set password to be the same as the old one"}), 400

    for char in PASSWORD_FORBIDDEN_CHARACTERS:
        if char in password:
            return jsonify({"error": "Forbidden character in password '" + char}), 400

    # check if password meets complexity requirements
    test = test_password(password)
    if test:
        return jsonify({"error": "Invalid password",
                        "tests": test}), 403

    user.update_password(password)
    db.session.commit()

    return jsonify({"message": "Password successfully reset! You can close this page."}), 200


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

    token = create_jwt(user.id)
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
