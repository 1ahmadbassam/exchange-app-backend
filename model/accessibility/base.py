from sqlalchemy import event
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker

from init import db, ma
from model.user import User


class Accessibility(db.Model):
    __tablename__ = 'accessibility'

    user_id: Mapped[int] = mapped_column(db.ForeignKey('user.id'), primary_key=True, nullable=False)
    inverted_colors: Mapped[bool] = mapped_column(nullable=False, default=False)
    sonification: Mapped[bool] = mapped_column(nullable=False, default=False)
    narration: Mapped[bool] = mapped_column(nullable=False, default=False)

    def __init__(self, user_id):
        super(Accessibility, self).__init__(user_id=user_id)


class AccessibilitySchema(ma.Schema):
    class Meta:
        fields = ('user_id', 'inverted_colors', 'sonification', 'narration')
        model = Accessibility


@event.listens_for(User, 'after_insert')
def create_accessibility(_, connection, target):
    session = sessionmaker(bind=connection)()
    session.add(Accessibility(target.id))
    session.commit()
