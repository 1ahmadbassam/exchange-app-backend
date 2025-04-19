from flask import Blueprint, jsonify, request

from init import limiter, db
from model.offer import Offer
from model.wallet import Wallet, WalletTransaction, WalletSchema, WalletInflightSchema, WalletTransactionSchema
from util.user import validate_token

wallet_bp = Blueprint('wallet', __name__, url_prefix='/wallet')
wallet_schema = WalletSchema()
wallet_inflight_schema = WalletInflightSchema()
wallet_transaction_schema = WalletTransactionSchema()
wallet_transactions_schema = WalletTransactionSchema(many=True)


@wallet_bp.route('', methods=['GET'])
@limiter.limit("10 per minute")
def get_wallet():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    wallet = db.session.query(Wallet).filter_by(user_id=user.id).first()
    return jsonify(wallet_schema.dump(wallet)), 200


@wallet_bp.route('/inflight', methods=['GET'])
@limiter.limit("10 per minute")
def get_wallet_inflight():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    wallet = db.session.query(Wallet).filter_by(user_id=user.id).first()
    return jsonify(wallet_inflight_schema.dump(wallet)), 200


@wallet_bp.route('/transaction', methods=['GET'])
@limiter.limit("10 per minute")
def get_wallet_transaction():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    wallet_transaction_id = request.args.get('id', '')
    if not wallet_transaction_id:
        return jsonify({"error": "Missing required parameters"}), 400
    wallet_transaction = db.session.query(WalletTransaction).filter_by(id=wallet_transaction_id).first()
    if not wallet_transaction:
        return jsonify({"error": "Invalid wallet transaction input"}), 400
    if wallet_transaction.user_id != int(user.id):
        return jsonify({"error": "Access is forbidden"}), 403
    return jsonify(wallet_transaction_schema.dump(wallet_transaction)), 200


@wallet_bp.route('/transactions', methods=['GET'])
@limiter.limit("10 per minute")
def get_wallet_transactions():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    wallet_transactions = db.session.query(WalletTransaction).filter_by(user_id=user.id).all()
    return jsonify(wallet_transactions_schema.dump(wallet_transactions)), 200


@wallet_bp.route('/transaction', methods=['POST'])
@limiter.limit("10 per minute")
def add_wallet_transaction():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    if (not request.json
            or ('usd_amount' not in request.json and 'lbp_amount' not in request.json)
            or 'description' not in request.json):
        return jsonify({"error": "Missing required fields"}), 400
    if 'usd_amount' in request.json:
        try:
            usd_amount = float(request.json['usd_amount'])
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid USD amount, must be a valid number"}), 400
    else:
        usd_amount = 0
    if 'lbp_amount' in request.json:
        try:
            lbp_amount = float(request.json['lbp_amount'])
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid LBP amount, must be a valid number"}), 400
    else:
        lbp_amount = 0
    description = request.json['description']
    wallet = db.session.query(Wallet).filter_by(user_id=user.id).first()
    if not wallet.has_enough_usd(usd_amount):
        return jsonify({"error": "Not enough USD for transaction"}), 401
    if not wallet.has_enough_lbp(lbp_amount):
        return jsonify({"error": "Not enough LBP for transaction"}), 401
    wl = WalletTransaction(usd_amount=usd_amount, lbp_amount=lbp_amount, description=description, user_id=user.id)
    db.session.add(wl)
    db.session.commit()
    return jsonify(wallet_transaction_schema.dump(wl)), 200


@wallet_bp.route('/reset', methods=['POST'])
@limiter.limit("10 per minute")
def reset_wallet():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    otp = request.json.get('otp', '')
    if not otp and user.mfa:
        return jsonify({"error": "TOTP Required"}), 401
    elif user.mfa and not user.is_otp_valid(otp):
        return jsonify({"error": "Invalid OTP"}), 403
    if db.session.query(Offer).filter_by(user_id=user.id, available=True).all():
        return jsonify({"error": "Cannot reset wallet with available offers"}), 401
    db.session.query(WalletTransaction).filter_by(user_id=user.id).delete()
    # just in case, rounding errors
    wallet = db.session.query(Wallet).filter_by(user_id=user.id).first()
    wallet.reset()
    db.session.commit()
    return '', 200


@wallet_bp.route('/transaction/delete', methods=['POST'])
@limiter.limit("10 per minute")
def delete_wallet_transaction():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    wallet_transaction = db.session.query(WalletTransaction).filter_by(user_id=user.id).all()
    if not wallet_transaction:
        return jsonify({"error": "No transactions found"}), 400
    wallet_transaction = wallet_transaction[-1]
    wallet = db.session.query(Wallet).filter_by(user_id=user.id).first()
    if not wallet.has_enough_usd(0, -wallet_transaction.usd_amount):
        return jsonify({"error": "Not enough USD balance to remove wallet transaction "
                                 "without removing outstanding offers "}), 401
    elif not wallet.has_enough_lbp(0, -wallet_transaction.lbp_amount):
        return jsonify({"error": "Not enough LBP balance to remove wallet transaction "
                                 "without removing outstanding offers "}), 401
    db.session.delete(wallet_transaction)
    db.session.commit()
    return '', 200
