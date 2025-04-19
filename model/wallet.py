import datetime

from sqlalchemy import String, event
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker

from init import db, tz, ma
from model.transaction import Transaction
from model.user import User


class Wallet(db.Model):
    __tablename__ = 'wallet'

    user_id: Mapped[int] = mapped_column(db.ForeignKey('user.id'), primary_key=True, nullable=False)
    usd_amount: Mapped[float] = mapped_column(nullable=False, default=0)
    usd_inflight: Mapped[float] = mapped_column(nullable=False, default=0)
    lbp_amount: Mapped[float] = mapped_column(nullable=False, default=0)
    lbp_inflight: Mapped[float] = mapped_column(nullable=False, default=0)

    __wallet_transactions = db.relationship("WalletTransaction", cascade="all, delete", backref="wallet")

    def __init__(self, user_id):
        super(Wallet, self).__init__(user_id=user_id)
        self.usd_amount = 0
        self.lbp_amount = 0

    def has_enough_lbp(self, lbp_amount, lbp_exc=0):
        return lbp_amount > 0 or self.lbp_amount + self.lbp_inflight + lbp_exc >= abs(lbp_amount)

    def has_enough_usd(self, usd_amount, usd_exc=0):
        return usd_amount > 0 or self.usd_amount + self.usd_inflight + usd_exc >= abs(usd_amount)

    def add_inflight(self, usd_amount=0, lbp_amount=0, usd_to_lbp=False):
        self.usd_inflight += -usd_amount if usd_to_lbp else 0
        self.lbp_inflight += 0 if usd_to_lbp else -lbp_amount

    def remove_inflight(self, usd_amount=0, lbp_amount=0, usd_to_lbp=False):
        self.usd_inflight += usd_amount if usd_to_lbp else 0
        self.lbp_inflight += 0 if usd_to_lbp else lbp_amount

    def reset(self):
        self.usd_amount = 0
        self.lbp_amount = 0
        self.usd_inflight = 0
        self.lbp_inflight = 0


class WalletTransaction(db.Model):
    __tablename__ = 'wallet_transaction'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usd_amount: Mapped[float] = mapped_column(nullable=False, default=0.0)
    lbp_amount: Mapped[float] = mapped_column(nullable=False, default=0.0)
    added_date: Mapped[datetime.datetime] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(db.ForeignKey('wallet.user_id'), nullable=False)
    description: Mapped[str] = mapped_column(String(128), nullable=False)

    def __init__(self, usd_amount, lbp_amount, user_id, description, added_date=datetime.datetime.now(tz)):
        super(WalletTransaction, self).__init__(usd_amount=usd_amount,
                                                lbp_amount=lbp_amount,
                                                user_id=user_id,
                                                description=description,
                                                added_date=added_date)


class WalletSchema(ma.Schema):
    class Meta:
        fields = ("user_id", "usd_amount", "lbp_amount")
        model = Wallet


class WalletInflightSchema(ma.Schema):
    class Meta:
        fields = ("user_id", "usd_inflight", "lbp_inflight")
        model = Wallet


class WalletTransactionSchema(ma.Schema):
    class Meta:
        fields = ("id", "usd_amount", "lbp_amount", "added_date", "user_id", "description")
        model = WalletTransaction


@event.listens_for(User, 'after_insert')
def create_wallet(_, connection, target):
    session = sessionmaker(bind=connection)()
    session.add(Wallet(target.id))
    session.commit()


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


@event.listens_for(WalletTransaction, 'after_insert')
def insert_in_wallet(_, connection, target):
    session = sessionmaker(bind=connection)()
    wallet = session.query(Wallet).filter_by(user_id=target.user_id).first()
    wallet.usd_amount += target.usd_amount
    wallet.lbp_amount += target.lbp_amount
    session.commit()


@event.listens_for(WalletTransaction, 'after_delete')
def remove_from_wallet(_, connection, target):
    session = sessionmaker(bind=connection)()
    wallet = session.query(Wallet).filter_by(user_id=target.user_id).first()
    wallet.usd_amount -= target.usd_amount
    wallet.lbp_amount -= target.lbp_amount
    session.commit()
