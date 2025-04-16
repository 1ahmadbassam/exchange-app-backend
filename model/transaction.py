import datetime

from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from init import db, ma, tz


class Transaction(db.Model):
    __tablename__ = 'transaction'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usd_amount: Mapped[float] = mapped_column(nullable=False)
    lbp_amount: Mapped[float] = mapped_column(nullable=False)
    usd_to_lbp: Mapped[bool] = mapped_column(nullable=False)
    added_date: Mapped[datetime.datetime] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(db.ForeignKey('user.id'), nullable=True)

    __table_args__ = (CheckConstraint('usd_amount > 0', name='usd_amount_positive'),
                      CheckConstraint('lbp_amount > 0', name='lbp_amount_positive'),)

    def __init__(self, usd_amount, lbp_amount, usd_to_lbp, user_id, added_date=datetime.datetime.now(tz)):
        super(Transaction, self).__init__(usd_amount=usd_amount,
                                          lbp_amount=lbp_amount,
                                          usd_to_lbp=usd_to_lbp,
                                          user_id=user_id,
                                          added_date=added_date)


class TransactionSchema(ma.Schema):
    class Meta:
        fields = ("id", "usd_amount", "lbp_amount", "usd_to_lbp", "user_id", "added_date")
        model = Transaction
