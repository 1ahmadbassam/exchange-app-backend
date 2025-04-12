import statistics
import datetime

from flask import Blueprint, jsonify, request
from init import limiter, db
from model.transaction import Transaction

exchange_bp = Blueprint('exchange', __name__)

def get_exchange_rate(end_date=datetime.datetime.now(datetime.timezone.utc)):
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
    return usd_to_lbp, lbp_to_usd

@exchange_bp.route('/exchangeRate', methods=['GET'])
@limiter.limit("10 per minute")
def exchange_rate():
    usd_to_lbp, lbp_to_usd = get_exchange_rate()
    return jsonify({'usd_to_lbp': usd_to_lbp if usd_to_lbp else None, 'lbp_to_usd': lbp_to_usd if lbp_to_usd else None}), 200

@exchange_bp.route('/exchangeRate/hourly', methods=['GET'])
@limiter.limit("10 per minute")
def exchange_rate_hourly():
    rates = []
    for i in range(24):
        hour = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=i)
        usd_to_lbp, lbp_to_usd = get_exchange_rate(hour)
        rates.append({
            "datetime": hour.isoformat().replace("+00:00", "Z"),
            "usd_to_lbp": usd_to_lbp,
            "lbp_to_usd": lbp_to_usd
        })
    return jsonify(rates), 200

@exchange_bp.route('/exchangeRate/daily', methods=['GET'])
@limiter.limit("10 per minute")
def exchange_rate_daily():
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
    rates = []

    today = datetime.datetime.now(datetime.timezone.utc)
    # append today's (incomplete) rate
    if today.date() == end_date.date():
        usd_to_lbp, lbp_to_usd = get_exchange_rate(today)
        rates.append({
            "date": str(today.date()),
            "usd_to_lbp": usd_to_lbp,
            "lbp_to_usd": lbp_to_usd
        })
    else:
        # force end_date to be included
        end_date = end_date + datetime.timedelta(days=1)

    while end_date > start_date:
        usd_to_lbp, lbp_to_usd = get_exchange_rate(end_date)
        end_date -= datetime.timedelta(days=1)
        rates.append({
            "date": str(end_date.date()),
            "usd_to_lbp": usd_to_lbp,
            "lbp_to_usd": lbp_to_usd
        })
    return jsonify(rates), 200
