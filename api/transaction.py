import jwt
from flask import Blueprint, request, jsonify, abort

from init import db, limiter
from model.transaction import Transaction, TransactionSchema
from util.token import extract_auth_token, decode_token

transaction_schema = TransactionSchema()
transactions_schema = TransactionSchema(many=True)

transaction_bp = Blueprint('transaction', __name__)


@transaction_bp.route('/transaction', methods=['POST'])
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
            abort(403)
    transaction = Transaction(usd_amount=usd_amount, lbp_amount=lbp_amount, usd_to_lbp=usd_to_lbp, user_id=user_id)
    db.session.add(transaction)
    db.session.commit()
    return jsonify(transaction_schema.dump(transaction)), 200


@transaction_bp.route('/transaction', methods=['GET'])
@limiter.limit("10 per minute")
def get_all_transactions():
    token = extract_auth_token(request)
    if not token:
        abort(403)
    try:
        user_id = decode_token(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        abort(403)
    transactions = db.session.query(Transaction).filter_by(user_id=user_id).all()
    return jsonify(transactions_schema.dump(transactions)), 200
