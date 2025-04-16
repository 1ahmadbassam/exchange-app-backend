import datetime
import statistics

from dateutil.relativedelta import relativedelta
from flask import Blueprint, jsonify, request

from init import limiter, db, tz
from model.rate import DailyRate, MonthlyRate
from model.transaction import Transaction
from util.exchange import VOLATILITY_MSG, TREND_MSG

exchange_bp = Blueprint('exchange', __name__)


def _get_exchange_rate(end_date=datetime.datetime.now(tz)):
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


def _get_monthly_exchange_rate(month: datetime.datetime = None):
    if not month:
        month = datetime.datetime.now(tz)
    usd_to_lbp_rates = []
    lbp_to_usd_rates = []
    cur = month
    # works for current date and past ones, because they are in the past
    while cur < month + relativedelta(months=1) and cur <= datetime.datetime.now(tz):
        usd_to_lbp, lbp_to_usd = get_daily_exchange_rate(cur)
        usd_to_lbp_rates.append(usd_to_lbp)
        lbp_to_usd_rates.append(lbp_to_usd)
        cur = cur + datetime.timedelta(days=1)
    try:
        usd_to_lbp = statistics.mean([x for x in usd_to_lbp_rates if x is not None])
    except statistics.StatisticsError:
        usd_to_lbp = None
    try:
        lbp_to_usd = statistics.mean([x for x in lbp_to_usd_rates if x is not None])
    except statistics.StatisticsError:
        lbp_to_usd = None
    # precision reasons
    return None if usd_to_lbp is None else round(usd_to_lbp, 6), None if lbp_to_usd is None else round(lbp_to_usd, 6)


def get_daily_exchange_rate(day: datetime.datetime = None):
    # do not cache for today, today isn't done yet
    if not day or day.date() == datetime.datetime.now(tz).date():
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
    if not month or (
            month.month == datetime.datetime.now(tz).month
            and month.year == datetime.datetime.now(tz).year
    ):
        return _get_monthly_exchange_rate()
    # any day in the month works
    month = datetime.datetime(month.year, month.month, 1, tzinfo=tz)
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
        hour = datetime.datetime.now(tz) - datetime.timedelta(hours=i)
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

    today = datetime.datetime.now(tz)
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
    today = datetime.datetime.now(tz)
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
    return jsonify({"period": period,
                    "usd_to_lbp": {
                        "former_rate": usd_to_lbp_former,
                        "current_rate": usd_to_lbp,
                        "percentage_change": usd_to_lbp_delta,
                        "message": TREND_MSG.format("USD-LBP",
                                                    "risen" if usd_to_lbp_delta > 1e-6 else "fell",
                                                    round(usd_to_lbp_former, 2),
                                                    round(usd_to_lbp, 2),
                                                    round(abs(usd_to_lbp_delta), 2),
                                                    period)
                        if usd_to_lbp_delta is not None else "Rates missing."},
                    "lbp_to_usd": {
                        "former_rate": lbp_to_usd_former,
                        "current_rate": lbp_to_usd,
                        "percentage_change": lbp_to_usd_delta,
                        "message": TREND_MSG.format("LBP-USD",
                                                    "risen" if lbp_to_usd_delta > 1e-6 else "fell",
                                                    round(lbp_to_usd_former, 2),
                                                    round(lbp_to_usd, 2),
                                                    round(abs(lbp_to_usd_delta), 2),
                                                    period)
                        if lbp_to_usd_delta is not None else "Rates missing."}
                    })


@exchange_bp.route('/exchangeRate/volatility', methods=['GET'])
@limiter.limit("10 per minute")
def exchange_rate_volatility():
    period = request.args.get("period", "").strip()
    if not period:
        return jsonify({'error': 'period is required'}), 400
    end_date = datetime.datetime.now(tz)
    exact = True
    if period == "24h":
        start_date = end_date - datetime.timedelta(hours=24)
    elif period == "7d":
        start_date = end_date - datetime.timedelta(days=7)
    elif period == "30d":
        start_date = end_date - datetime.timedelta(days=30)
    elif period == "3mon":
        start_date = end_date - relativedelta(months=3)
        exact = False
    elif period == "6mon":
        start_date = end_date - relativedelta(months=6)
        exact = False
    elif period == "1yr":
        start_date = end_date - relativedelta(years=1)
        exact = False
    else:
        return jsonify({'error': 'period is invalid'}), 400
    usd_to_lbp_rates = []
    lbp_to_usd_rates = []
    while start_date <= end_date:
        usd_to_lbp, lbp_to_usd = _get_exchange_rate(start_date) if exact else get_daily_exchange_rate(start_date)
        usd_to_lbp_rates.append(usd_to_lbp)
        lbp_to_usd_rates.append(lbp_to_usd)
        start_date += datetime.timedelta(days=1) if period != "24h" else datetime.timedelta(hours=1)
    usd_to_lbp_rates = [x for x in usd_to_lbp_rates if x is not None]
    lbp_to_usd_rates = [x for x in lbp_to_usd_rates if x is not None]
    try:
        usd_to_lbp_sd = statistics.stdev(usd_to_lbp_rates)
    except statistics.StatisticsError:
        usd_to_lbp_sd = None
    try:
        lbp_to_usd_sd = statistics.stdev(lbp_to_usd_rates)
    except statistics.StatisticsError:
        lbp_to_usd_sd = None

    try:
        usd_to_lbp_max = max(usd_to_lbp_rates)
    except ValueError:
        usd_to_lbp_max = None
    try:
        lbp_to_usd_max = max(lbp_to_usd_rates)
    except ValueError:
        lbp_to_usd_max = None

    try:
        usd_to_lbp_min = min(usd_to_lbp_rates)
    except ValueError:
        usd_to_lbp_min = None
    try:
        lbp_to_usd_min = min(lbp_to_usd_rates)
    except ValueError:
        lbp_to_usd_min = None
    return jsonify({"period": period,
                    "usd_to_lbp": {
                        "standard_deviation": usd_to_lbp_sd,
                        "min_rate": usd_to_lbp_min,
                        "max_rate": usd_to_lbp_max,
                        "message": VOLATILITY_MSG.format("USD-LBP",
                                                         "slightly" if usd_to_lbp_sd < (1000 + 1e-6) else "greatly",
                                                         round(usd_to_lbp_min, 2),
                                                         round(usd_to_lbp_max, 2),
                                                         period)
                        if usd_to_lbp_sd is not None else "Rates missing."},
                    "lbp_to_usd": {
                        "standard_deviation": lbp_to_usd_sd,
                        "min_rate": lbp_to_usd_min,
                        "max_rate": lbp_to_usd_max,
                        "message": VOLATILITY_MSG.format("LBP-USD",
                                                         "slightly" if lbp_to_usd_sd < (1000 + 1e-6) else "greatly",
                                                         round(lbp_to_usd_min, 2),
                                                         round(lbp_to_usd_max, 2),
                                                         period)
                        if lbp_to_usd_sd is not None else "Rates missing."}
                    })
