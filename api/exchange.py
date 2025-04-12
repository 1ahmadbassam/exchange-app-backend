import datetime
import statistics

from dateutil.relativedelta import relativedelta
from flask import Blueprint, jsonify, request

from init import limiter, db
from model.rate import DailyRate, MonthlyRate
from model.transaction import Transaction

MSG = "The {} exchange rate has {} from {} to {} by a factor of {}% over the past {}."

exchange_bp = Blueprint('exchange', __name__)


def _get_exchange_rate(end_date=datetime.datetime.now(datetime.timezone.utc)):
    print("[DEBUG] get_exchange_rate")
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
    # precision reasons
    return None if usd_to_lbp is None else round(usd_to_lbp, 6), None if lbp_to_usd is None else round(lbp_to_usd, 6)


def _get_monthly_exchange_rate(month):
    usd_to_lbp_rates = []
    lbp_to_usd_rates = []
    cur = month
    while cur < month + relativedelta(months=1):
        usd_to_lbp, lbp_to_usd = get_daily_exchange_rate(cur)
        usd_to_lbp_rates.append(usd_to_lbp)
        lbp_to_usd_rates.append(lbp_to_usd)
        cur = cur + datetime.timedelta(days=1)
    try:
        usd_to_lbp = statistics.mean([x for x in usd_to_lbp_rates if x])
    except statistics.StatisticsError:
        usd_to_lbp = None
    try:
        lbp_to_usd = statistics.mean([x for x in lbp_to_usd_rates if x])
    except statistics.StatisticsError:
        lbp_to_usd = None
    # precision reasons
    return None if usd_to_lbp is None else round(usd_to_lbp, 6), None if lbp_to_usd is None else round(lbp_to_usd, 6)


def get_daily_exchange_rate(day: datetime.datetime = None):
    # do not cache for today, today isn't done yet
    if not day or day.date() == datetime.datetime.now(datetime.timezone.utc).date():
        return _get_exchange_rate()
    day = day.replace(hour=0, minute=0, second=0, microsecond=0)
    item = db.session.query(DailyRate).filter_by(date=day.date()).scalar()
    if not item:
        # adjustment: +1 days, to count midnight next day
        usd_to_lbp, lbp_to_usd = _get_exchange_rate(day + datetime.timedelta(days=1))
        rate = DailyRate(date=day.date(), usd_to_lbp=usd_to_lbp, lbp_to_usd=lbp_to_usd)
        db.session.add(rate)
        db.session.commit()
        return usd_to_lbp, lbp_to_usd
    return None if item.usd_to_lbp is None else float(item.usd_to_lbp), None if item.lbp_to_usd is None else float(
        item.lbp_to_usd)


def get_monthly_exchange_rate(month: datetime.datetime = None):
    if not month or month.month == datetime.datetime.now(datetime.timezone.utc).month:
        return _get_exchange_rate()
    # any day in the month works
    month = datetime.datetime(month.year, month.month, 1, tzinfo=datetime.timezone.utc)
    item = db.session.query(MonthlyRate).filter_by(date=month.date()).scalar()
    if not item:
        usd_to_lbp, lbp_to_usd = _get_monthly_exchange_rate(month)
        rate = MonthlyRate(date=month.date(), usd_to_lbp=usd_to_lbp, lbp_to_usd=lbp_to_usd)
        db.session.add(rate)
        db.session.commit()
        return usd_to_lbp, lbp_to_usd
    return None if item.usd_to_lbp is None else float(item.usd_to_lbp), None if item.lbp_to_usd is None else float(
        item.lbp_to_usd)


@exchange_bp.route('/exchangeRate', methods=['GET'])
@limiter.limit("10 per minute")
def exchange_rate():
    usd_to_lbp, lbp_to_usd = get_daily_exchange_rate()
    return jsonify({'usd_to_lbp': usd_to_lbp, 'lbp_to_usd': lbp_to_usd}), 200


@exchange_bp.route('/exchangeRate/hourly', methods=['GET'])
@limiter.limit("10 per minute")
def exchange_rate_hourly():
    rates = []
    for i in range(24):
        hour = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=i)
        usd_to_lbp, lbp_to_usd = _get_exchange_rate(hour)
        rates.append(
            {"datetime": hour.isoformat().replace("+00:00", "Z"), "usd_to_lbp": usd_to_lbp, "lbp_to_usd": lbp_to_usd})
    return jsonify(rates[::-1]), 200


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
    at = False
    if today.date() == end_date.date():
        end_date -= datetime.timedelta(days=1)
        at = True

    while start_date <= end_date:
        usd_to_lbp, lbp_to_usd = get_daily_exchange_rate(start_date)
        rates.append({"date": str(start_date.date()), "usd_to_lbp": usd_to_lbp, "lbp_to_usd": lbp_to_usd})
        start_date += datetime.timedelta(days=1)

    # append today's (incomplete) rate
    if at:
        usd_to_lbp, lbp_to_usd = get_daily_exchange_rate()
        rates.append({"date": str(today.date()), "usd_to_lbp": usd_to_lbp, "lbp_to_usd": lbp_to_usd})
    return jsonify(rates), 200


@exchange_bp.route('/exchangeRate/monthly', methods=['GET'])
@limiter.limit("10 per minute")
def exchange_rate_monthly():
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

    while start_date <= end_date:
        usd_to_lbp, lbp_to_usd = get_monthly_exchange_rate(start_date)
        rates.append({"date": str(start_date.date()), "usd_to_lbp": usd_to_lbp, "lbp_to_usd": lbp_to_usd})
        start_date += relativedelta(months=1)
    return jsonify(rates), 200


@exchange_bp.route('/exchangeRate/trend', methods=['GET'])
@limiter.limit("10 per minute")
def exchange_rate_trend():
    period = request.args.get("period", "").strip()
    if not period:
        return jsonify({'error': 'period is required'}), 400
    today = datetime.datetime.now(datetime.timezone.utc)
    if period == "24h":
        former_date = today - datetime.timedelta(hours=24)
    elif period == "7d":
        former_date = today - datetime.timedelta(days=7)
    elif period == "30d":
        former_date = today - datetime.timedelta(days=30)
    elif period == "3mon":
        former_date = today - relativedelta(months=3)
    elif period == "6mon":
        former_date = today - relativedelta(months=6)
    elif period == "1yr":
        former_date = today - relativedelta(years=1)
    else:
        return jsonify({'error': 'period is invalid'}), 400
    usd_to_lbp_former, lbp_to_usd_former = _get_exchange_rate(former_date)
    usd_to_lbp, lbp_to_usd = _get_exchange_rate()
    if usd_to_lbp and usd_to_lbp_former:
        usd_to_lbp_delta = 100 * (usd_to_lbp - usd_to_lbp_former) / usd_to_lbp_former
    else:
        usd_to_lbp_delta = None
    if lbp_to_usd and lbp_to_usd_former:
        lbp_to_usd_delta = 100 * (lbp_to_usd - lbp_to_usd_former) / lbp_to_usd_former
    else:
        lbp_to_usd_delta = None
    return jsonify({"period": period, "usd_to_lbp": {"former_rate": usd_to_lbp_former, "current_rate": usd_to_lbp,
        "percentage_change": usd_to_lbp_delta,
        "message": MSG.format("USD-LBP", "risen" if usd_to_lbp_delta > 1e-6 else "fell", round(usd_to_lbp_former, 2),
                              round(usd_to_lbp, 2), round(abs(usd_to_lbp_delta), 2),
                              period) if usd_to_lbp_delta is not None else "Rates missing."},
        "lbp_to_usd": {"former_rate": lbp_to_usd_former, "current_rate": lbp_to_usd,
            "percentage_change": lbp_to_usd_delta,
            "message": MSG.format("LBP-USD", "risen" if lbp_to_usd_delta > 1e-6 else "fell",
                                  round(lbp_to_usd_former, 2), round(lbp_to_usd, 2), round(abs(lbp_to_usd_delta), 2),
                                  period) if lbp_to_usd_delta is not None else "Rates missing."}})
