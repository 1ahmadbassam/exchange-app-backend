import datetime

from init import db, tz
from model.transaction import Transaction
from model.volume import DailyVolume, MonthlyVolume


def get_transaction_volume(start_date, end_date):
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
    return get_transaction_volume(start_date, end_date)


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
    return get_transaction_volume(start_date, end_date)


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
