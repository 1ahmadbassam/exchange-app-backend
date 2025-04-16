import datetime
import statistics

from dateutil.relativedelta import relativedelta

from init import tz, db
from model.rate import MonthlyRate, DailyRate
from model.transaction import Transaction

TREND_MSG = "The {} exchange rate has {} from {} to {} by a factor of {}% over the past {}."
VOLATILITY_MSG = "The {} exchange rate varied {} and ranged between {} and {} over the past {}. "


def get_exchange_rate(end_date=datetime.datetime.now(tz)):
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
        return get_exchange_rate()
    day = day.replace(hour=0, minute=0, second=0, microsecond=0)
    item = db.session.query(DailyRate).filter_by(date=day.date()).scalar()
    if not item:
        # adjustment: +1 days, to count midnight next day
        usd_to_lbp, lbp_to_usd = get_exchange_rate(day + datetime.timedelta(days=1))
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
