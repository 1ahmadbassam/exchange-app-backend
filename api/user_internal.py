import datetime

from flask import render_template, jsonify, request, url_for, Blueprint

from init import limiter, db, bcrypt, tz
from model.user import User, UnconfirmedUser, UserSchema
from util.token import confirm_verification_token
from util.user import PASSWORD_FORBIDDEN_CHARACTERS, test_password

user_internal_bp = Blueprint('user_internal', __name__)
user_schema = UserSchema()

@user_internal_bp.route("/verify/<token>", methods=['GET'])
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
    user = User(user_name=u_user.user_name,
                password=u_user.hashed_password,
                email=email,
                created_at=u_user.created_at,
                verified_at=datetime.datetime.now(tz),
                hsh=False)
    db.session.add(user)
    db.session.delete(u_user)
    db.session.commit()
    return render_template("verify.html"), 200


@user_internal_bp.route("/reset/<token>", methods=['GET'])
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
    return render_template("reset.html", reset_url=url_for("user_internal.password_reset", token=token, _external=True)), 200


@user_internal_bp.route("/reset/<token>", methods=['POST'])
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
