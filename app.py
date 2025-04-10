import datetime
import statistics
import traceback

import jwt
from flask import request, jsonify, abort

from init import app, SECRET_KEY, db, limiter, bcrypt
from model.transaction import Transaction, TransactionSchema
from model.user import User, UserSchema

transaction_schema = TransactionSchema()
user_schema = UserSchema()
transactions_schema = TransactionSchema(many=True)


def create_token(user_id):
    payload = {
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=4),
        'iat': datetime.datetime.now(datetime.timezone.utc),
        'sub': str(user_id)
    }
    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm='HS256'
    )


def extract_auth_token(authenticated_request):
    auth_header = authenticated_request.headers.get('Authorization')
    if auth_header:
        return auth_header.split(" ")[1].strip()
    else:
        return None


def decode_token(token):
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    return payload['sub']


@app.route('/transaction', methods=['POST'])
@limiter.limit("10 per minute")
def add_transaction():
    usd_amount = float(request.json['usd_amount'])
    if usd_amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    lbp_amount = float(request.json['lbp_amount'])
    if lbp_amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    usd_to_lbp = bool(request.json['usd_to_lbp'])
    token = extract_auth_token(request)
    user_id = None
    if token is not None:
        try:
            user_id = decode_token(token)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            traceback.print_exc()
            abort(403)
    transaction = Transaction(usd_amount=usd_amount, lbp_amount=lbp_amount, usd_to_lbp=usd_to_lbp, user_id=user_id)
    db.session.add(transaction)
    db.session.commit()
    return jsonify(transaction_schema.dump(transaction)), 200


@app.route('/transaction', methods=['GET'])
@limiter.limit("10 per minute")
def get_all_transactions():
    token = extract_auth_token(request)
    if not token:
        abort(403)
    try:
        user_id = decode_token(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        traceback.print_exc()
        abort(403)
    transactions = db.session.query(Transaction).filter_by(user_id=user_id).all()
    return jsonify(transactions_schema.dump(transactions)), 200


@app.route('/exchangeRate', methods=['GET'])
@limiter.limit("10 per minute")
def exchange_rate():
    end_date = datetime.datetime.now(datetime.timezone.utc)
    start_date = end_date - datetime.timedelta(hours=72)

    try:
        usd_to_lbp = statistics.mean(map(lambda transact: transact.lbp_amount / transact.usd_amount, db.session.execute(
            db.select(Transaction).filter(Transaction.added_date.between(start_date, end_date),
                                          Transaction.usd_to_lbp)).scalars()))
    except statistics.StatisticsError:
        usd_to_lbp = None
    try:
        lbp_to_usd = statistics.mean(map(lambda transact: transact.lbp_amount / transact.usd_amount, db.session.execute(
            db.select(Transaction).filter(Transaction.added_date.between(start_date, end_date),
                                          Transaction.usd_to_lbp == False)).scalars()))
    except statistics.StatisticsError:
        lbp_to_usd = None
    return jsonify({'usd_to_lbp': usd_to_lbp if usd_to_lbp else None,
                    'lbp_to_usd': lbp_to_usd if lbp_to_usd else None})


@app.route('/user', methods=['POST'])
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


@app.route('/authentication', methods=['POST'])
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


if __name__ == "__main__":
    #with app.app_context():
    #    db.create_all()
    app.run(debug=False)
