import datetime

from sqlalchemy.orm import Mapped, mapped_column

from init import db, ma


class DailyVolume(db.Model):
    __tablename__ = 'dailyvolume'

    date: Mapped[datetime.date] = mapped_column(primary_key=True, nullable=False)
    usd_to_lbp_total_amount: Mapped[float] = mapped_column(nullable=False)
    usd_to_lbp_transaction_count: Mapped[int] = mapped_column(nullable=False)
    lbp_to_usd_total_amount: Mapped[float] = mapped_column(nullable=False)
    lbp_to_usd_transaction_count: Mapped[int] = mapped_column(nullable=False)

    def __init__(self, usd_to_lbp_total_amount, usd_to_lbp_transaction_count,
                 lbp_to_usd_total_amount, lbp_to_usd_transaction_count, date):
        super(DailyVolume, self).__init__(date=date,
                                          usd_to_lbp_total_amount=usd_to_lbp_total_amount,
                                          usd_to_lbp_transaction_count=usd_to_lbp_transaction_count,
                                          lbp_to_usd_total_amount=lbp_to_usd_total_amount,
                                          lbp_to_usd_transaction_count=lbp_to_usd_transaction_count)


class DailyVolumeSchema(ma.Schema):
    class Meta:
        fields = ("date",
                  "usd_to_lbp_total_amount", "usd_to_lbp_transaction_count",
                  "lbp_to_usd_total_amount", "lbp_to_usd_transaction_count")
        model = DailyVolume


class MonthlyVolume(db.Model):
    __tablename__ = 'monthlyvolume'

    date: Mapped[datetime.date] = mapped_column(primary_key=True, nullable=False)
    usd_to_lbp_total_amount: Mapped[float] = mapped_column(nullable=False)
    usd_to_lbp_transaction_count: Mapped[int] = mapped_column(nullable=False)
    lbp_to_usd_total_amount: Mapped[float] = mapped_column(nullable=False)
    lbp_to_usd_transaction_count: Mapped[int] = mapped_column(nullable=False)

    def __init__(self, usd_to_lbp_total_amount, usd_to_lbp_transaction_count,
                 lbp_to_usd_total_amount, lbp_to_usd_transaction_count, date):
        super(MonthlyVolume, self).__init__(date=date,
                                          usd_to_lbp_total_amount=usd_to_lbp_total_amount,
                                          usd_to_lbp_transaction_count=usd_to_lbp_transaction_count,
                                          lbp_to_usd_total_amount=lbp_to_usd_total_amount,
                                          lbp_to_usd_transaction_count=lbp_to_usd_transaction_count)


class MonthlyVolumeSchema(ma.Schema):
    class Meta:
        fields = ("date",
                  "usd_to_lbp_total_amount", "usd_to_lbp_transaction_count",
                  "lbp_to_usd_total_amount", "lbp_to_usd_transaction_count")
        model = MonthlyVolume
