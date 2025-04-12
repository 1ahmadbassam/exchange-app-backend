import datetime

from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column

from init import db, ma


class DailyRate(db.Model):
    __tablename__ = 'dailyrate'

    date: Mapped[datetime.date] = mapped_column(primary_key=True, nullable=False)
    usd_to_lbp = db.Column(Numeric(precision=24, scale=6), nullable=True)
    lbp_to_usd = db.Column(Numeric(precision=24, scale=6), nullable=True)

    def __init__(self, usd_to_lbp, lbp_to_usd, date):
        super(DailyRate, self).__init__(date=date, usd_to_lbp=usd_to_lbp, lbp_to_usd=lbp_to_usd)


class DailyRateSchema(ma.Schema):
    class Meta:
        fields = ("date", "usd_to_lbp", "lbp_to_usd")
        model = DailyRate


class MonthlyRate(db.Model):
    __tablename__ = 'monthlyrate'

    date: Mapped[datetime.date] = mapped_column(primary_key=True, nullable=False)
    usd_to_lbp = db.Column(Numeric(precision=24, scale=6), nullable=True)
    lbp_to_usd = db.Column(Numeric(precision=24, scale=6), nullable=True)

    def __init__(self, usd_to_lbp, lbp_to_usd, date):
        super(MonthlyRate, self).__init__(date=date, usd_to_lbp=usd_to_lbp, lbp_to_usd=lbp_to_usd)


class MonthlyRateSchema(ma.Schema):
    class Meta:
        fields = ("date", "usd_to_lbp", "lbp_to_usd")
        model = MonthlyRate
