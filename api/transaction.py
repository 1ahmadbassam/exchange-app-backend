import datetime

import jwt
from dateutil.relativedelta import relativedelta
from flask import Blueprint, request, jsonify

from init import db, limiter, tz
from model.transaction import Transaction, TransactionSchema
from model.volume import DailyVolume, MonthlyVolume
from util.token import extract_auth_jwt, decode_jwt

transaction_schema = TransactionSchema()
transactions_schema = TransactionSchema(many=True)

transaction_bp = Blueprint('transaction', __name__)


def _get_transaction_volume(start_date, end_date):
    usd_to_lbp = db.session.execute(db.select(Transaction).filter(Transaction.added_date.between(start_date, end_date),
                                                                  Transaction.usd_to_lbp)).scalars()
    usd_to_lbp_transaction_count = 0
    usd_to_lbp_total_amount = 0

    for transact in usd_to_lbp:
        usd_to_lbp_total_amount += transact.usd_amount
        usd_to_lbp_transaction_count += 1

    lbp_to_usd = db.session.execute(db.select(Transaction).filter(Transaction.added_date.between(start_date, end_date),
                                                                  Transaction.usd_to_lbp == False)).scalars()
    lbp_to_usd_transaction_count = 0
    lbp_to_usd_total_amount = 0

    for transact in lbp_to_usd:
        lbp_to_usd_total_amount += transact.lbp_amount
        lbp_to_usd_transaction_count += 1

    return ((usd_to_lbp_total_amount, usd_to_lbp_transaction_count),
            (lbp_to_usd_total_amount, lbp_to_usd_transaction_count))


def _get_daily_transaction_volume(end_date=datetime.datetime.now(tz)):
    start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    return _get_transaction_volume(start_date, end_date)


def get_daily_transaction_volume(day: datetime.datetime = None):
    if not day or day.date() == datetime.datetime.now(tz).date():
        return _get_daily_transaction_volume()
    day = day.replace(hour=0, minute=0, second=0, microsecond=0)
    item = db.session.query(DailyVolume).filter_by(date=day.date()).scalar()
    if not item:
        ((usd_to_lbp_total_amount, usd_to_lbp_transaction_count),
         (lbp_to_usd_total_amount, lbp_to_usd_transaction_count)) = _get_daily_transaction_volume(
            day + datetime.timedelta(days=1)
            - datetime.timedelta(microseconds=1))
        volume = DailyVolume(date=day.date(),
                             usd_to_lbp_total_amount=usd_to_lbp_total_amount,
                             usd_to_lbp_transaction_count=usd_to_lbp_transaction_count,
                             lbp_to_usd_total_amount=lbp_to_usd_total_amount,
                             lbp_to_usd_transaction_count=lbp_to_usd_transaction_count)
        db.session.add(volume)
        db.session.commit()
        return ((usd_to_lbp_total_amount, usd_to_lbp_transaction_count),
                (lbp_to_usd_total_amount, lbp_to_usd_transaction_count))
    return ((item.usd_to_lbp_total_amount, item.usd_to_lbp_transaction_count),
            (item.lbp_to_usd_total_amount, item.lbp_to_usd_transaction_count))


def _get_monthly_transaction_volume(end_date=datetime.datetime.now(tz)):
    start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return _get_transaction_volume(start_date, end_date)


def get_monthly_transaction_volume(month: datetime.datetime = None):
    if not month or (
            month.month == datetime.datetime.now(tz).month
            and month.year == datetime.datetime.now(tz).year
    ):
        return _get_monthly_transaction_volume()
    month = month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    item = db.session.query(MonthlyVolume).filter_by(date=month.date()).scalar()
    if not item:
        from dateutil.relativedelta import relativedelta
        ((usd_to_lbp_total_amount, usd_to_lbp_transaction_count),
         (lbp_to_usd_total_amount, lbp_to_usd_transaction_count)) = _get_monthly_transaction_volume(
            month + relativedelta(months=1)
            - datetime.timedelta(microseconds=1))
        volume = MonthlyVolume(date=month.date(),
                               usd_to_lbp_total_amount=usd_to_lbp_total_amount,
                               usd_to_lbp_transaction_count=usd_to_lbp_transaction_count,
                               lbp_to_usd_total_amount=lbp_to_usd_total_amount,
                               lbp_to_usd_transaction_count=lbp_to_usd_transaction_count)
        db.session.add(volume)
        db.session.commit()
        return ((usd_to_lbp_total_amount, usd_to_lbp_transaction_count),
                (lbp_to_usd_total_amount, lbp_to_usd_transaction_count))
    return ((item.usd_to_lbp_total_amount, item.usd_to_lbp_transaction_count),
            (item.lbp_to_usd_total_amount, item.lbp_to_usd_transaction_count))


@transaction_bp.route('/transaction', methods=['POST'])
@limiter.limit("10 per minute")
def add_transaction():
    if not request.json or 'usd_amount' not in request.json or 'lbp_amount' not in request.json or 'usd_to_lbp' not in request.json:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        usd_amount = float(request.json['usd_amount'])
        if usd_amount <= 1e-6:
            return jsonify({"error": "Invalid USD amount, must be greater than zero"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid USD amount, must be a valid number"}), 400

    try:
        lbp_amount = float(request.json['lbp_amount'])
        if lbp_amount <= 1e-6:
            return jsonify({"error": "Invalid LBP amount, must be greater than zero"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid LBP amount, must be a valid number"}), 400

    try:
        usd_to_lbp = bool(request.json['usd_to_lbp'])
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid usd_to_lbp, must be a boolean value"}), 400
    token = extract_auth_jwt(request)
    user_id = None
    if token is not None:
        try:
            user_id = decode_jwt(token)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return jsonify({"error": "Invalid or expired token"}), 403
    transaction = Transaction(usd_amount=usd_amount, lbp_amount=lbp_amount, usd_to_lbp=usd_to_lbp, user_id=user_id)
    db.session.add(transaction)
    db.session.commit()
    return jsonify(transaction_schema.dump(transaction)), 200


@transaction_bp.route('/transaction', methods=['GET'])
@limiter.limit("10 per minute")
def get_all_transactions():
    token = extract_auth_jwt(request)
    if not token:
        return jsonify({"error": "Invalid or expired token"}), 403
    try:
        user_id = decode_jwt(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return jsonify({"error": "Invalid or expired token"}), 403
    transactions = db.session.query(Transaction).filter_by(user_id=user_id).all()
    return jsonify(transactions_schema.dump(transactions)), 200


@transaction_bp.route('/transaction/volume/daily', methods=['GET'])
@limiter.limit("10 per minute")
def transaction_volume_daily():
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400
    if start_date > end_date:
        return jsonify({'error': 'start_date must be before end_date'}), 400
    try:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({'error': 'start_date and end_date are invalid'}), 400
    volumes = []

    while start_date <= end_date:
        ((usd_to_lbp_total_amount, usd_to_lbp_transaction_count),
         (lbp_to_usd_total_amount, lbp_to_usd_transaction_count)) = get_daily_transaction_volume(start_date)
        volumes.append({"date": str(start_date.date()),
                        "usd_to_lbp": {
                            "total_amount": usd_to_lbp_total_amount,
                            "transaction_count": usd_to_lbp_transaction_count,
                        },
                        "lbp_to_usd": {
                            "total_amount": lbp_to_usd_total_amount,
                            "transaction_count": lbp_to_usd_transaction_count,
                        }})
        start_date += datetime.timedelta(days=1)
    return jsonify(volumes), 200


@transaction_bp.route('/transaction/volume/monthly', methods=['GET'])
@limiter.limit("10 per minute")
def transaction_volume_monthly():
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400
    if start_date > end_date:
        return jsonify({'error': 'start_date must be before end_date'}), 400
    try:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({'error': 'start_date and end_date are invalid'}), 400
    volumes = []

    start_date = start_date.replace(day=1)
    end_date = end_date.replace(day=1)

    while start_date <= end_date:
        ((usd_to_lbp_total_amount, usd_to_lbp_transaction_count),
         (lbp_to_usd_total_amount, lbp_to_usd_transaction_count)) = get_monthly_transaction_volume(start_date)
        volumes.append({"date": str(start_date.date()),
                        "usd_to_lbp": {
                            "total_amount": usd_to_lbp_total_amount,
                            "transaction_count": usd_to_lbp_transaction_count,
                        },
                        "lbp_to_usd": {
                            "total_amount": lbp_to_usd_total_amount,
                            "transaction_count": lbp_to_usd_transaction_count,
                        }})
        start_date += relativedelta(months=1)
    return jsonify(volumes), 200
