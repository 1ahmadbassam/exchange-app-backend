import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from init import db, ma


class Offer(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usd_amount: Mapped[float] = mapped_column(nullable=False)
    lbp_amount: Mapped[float] = mapped_column(nullable=False)
    usd_to_lbp: Mapped[bool] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(db.ForeignKey('user.id'), nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    available: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(nullable=False)

    def __init__(self, usd_amount, lbp_amount, usd_to_lbp, user_id, location, phone_number,
                 created_at=datetime.datetime.now(datetime.timezone.utc)):
        super(Offer, self).__init__(usd_amount=usd_amount,
                                    lbp_amount=lbp_amount,
                                    usd_to_lbp=usd_to_lbp,
                                    user_id=user_id,
                                    location=location,
                                    phone_number=phone_number,
                                    available=True,
                                    created_at=created_at)


class OfferSchema(ma.Schema):
    class Meta:
        fields = ("id", "usd_amount", "lbp_amount", "usd_to_lbp", "user_id", "location", "phone_number", "available",
                  "created_at")
        model = Offer
