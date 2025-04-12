from flask import Blueprint, jsonify, abort, request

from init import limiter, db, bcrypt
from model.user import User, UserSchema
from util.token import create_token

user_bp = Blueprint('user', __name__)
user_schema = UserSchema()


@user_bp.route('/user', methods=['POST'])
@limiter.limit("10 per minute")
def create_user():
    user_name = request.json.get('user_name', '').strip()
    password = request.json.get('password', '').strip()

    if not user_name or not password:
        abort(400)

    if db.session.execute(db.select(User).filter_by(user_name=user_name)).scalar():
        return jsonify({"error": "User already exists"}), 400

    if len(user_name) > 30:
        return jsonify({"error": "Username too long"}), 400

    user = User(user_name=user_name, password=password)
    db.session.add(user)
    db.session.commit()
    return jsonify(user_schema.dump(user)), 200


@user_bp.route('/authentication', methods=['POST'])
@limiter.limit("10 per minute")
def authenticate_user():
    user_name = request.json.get('user_name', '').strip()
    password = request.json.get('password', '').strip()

    if not user_name or not password:
        abort(400)

    user = db.session.execute(db.select(User).filter_by(user_name=user_name)).scalar()

    if not user or not bcrypt.check_password_hash(user.hashed_password, password):
        abort(403)

    token = create_token(user.id)
    return jsonify({"token": token}), 200
