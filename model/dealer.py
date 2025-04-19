import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from init import db, ma


class Dealer(db.Model):
    __tablename__ = 'dealer'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lng: Mapped[float] = mapped_column(nullable=False)
    lat: Mapped[float] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    address: Mapped[str] = mapped_column(String(128), nullable=False)
    rating: Mapped[float] = mapped_column(nullable=False)
    usd_to_lbp: Mapped[float] = mapped_column(nullable=False)
    lbp_to_usd: Mapped[float] = mapped_column(nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[int] = mapped_column(db.ForeignKey('user.id'), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(nullable=False)

    def __init__(self, lng, lat, name, address, rating, usd_to_lbp, lbp_to_usd, user_id, phone_number,
                 created_at=datetime.datetime.now(datetime.timezone.utc)):
        super(Dealer, self).__init__(lat=lat,
                                     lng=lng,
                                     name=name,
                                     address=address,
                                     rating=rating,
                                     usd_to_lbp=usd_to_lbp,
                                     lbp_to_usd=lbp_to_usd,
                                     user_id=user_id,
                                     phone_number=phone_number,
                                     created_at=created_at)


class DealerSchema(ma.Schema):
    class Meta:
        fields = ("id", "lng", "lat", "name", "address", "rating",
                  "usd_to_lbp", "lbp_to_usd", "phone_number", "created_at")
        model = Dealer
