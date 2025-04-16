import datetime

from sqlalchemy import CheckConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker

from init import db, ma, tz
from model.wallet import WalletTransaction


class Transaction(db.Model):
    __tablename__ = 'transaction'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usd_amount: Mapped[float] = mapped_column(nullable=False)
    lbp_amount: Mapped[float] = mapped_column(nullable=False)
    usd_to_lbp: Mapped[bool] = mapped_column(nullable=False)
    added_date: Mapped[datetime.datetime] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(db.ForeignKey('user.id'), nullable=True)
    offer: Mapped[bool] = mapped_column(nullable=False, default=False)

    __table_args__ = (CheckConstraint('usd_amount > 0', name='usd_amount_positive'),
                      CheckConstraint('lbp_amount > 0', name='lbp_amount_positive'),)

    def __init__(self, usd_amount, lbp_amount, usd_to_lbp, user_id, added_date=datetime.datetime.now(tz), offer=False):
        super(Transaction, self).__init__(usd_amount=usd_amount,
                                          lbp_amount=lbp_amount,
                                          usd_to_lbp=usd_to_lbp,
                                          user_id=user_id,
                                          added_date=added_date,
                                          offer=offer)


class TransactionSchema(ma.Schema):
    class Meta:
        fields = ("id", "usd_amount", "lbp_amount", "usd_to_lbp", "user_id", "added_date")
        model = Transaction


@event.listens_for(Transaction, 'after_insert')
def update_wallet_transaction(_, connection, target):
    if target.user_id is not None and not target.offer:
        session = sessionmaker(bind=connection)()
        wl = WalletTransaction(usd_amount=-target.usd_amount if target.usd_to_lbp else target.usd_amount,
                               lbp_amount=target.lbp_amount if target.usd_to_lbp else -target.lbp_amount,
                               user_id=target.user_id,
                               added_date=target.added_date,
                               description="USD to LBP exchange" if target.usd_to_lbp else "LBP to USD exchange")
        session.add(wl)
        session.commit()
