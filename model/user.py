from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from init import db, ma, bcrypt


class User(db.Model):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)

    def __init__(self, user_name, password, email, hsh=True):
        super(User, self).__init__(user_name=user_name, email=email)
        self.hashed_password = bcrypt.generate_password_hash(password) if hsh else password


class UnconfirmedUser(db.Model):
    __tablename__ = 'unconfirmed_user'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)

    def __init__(self, user_name, password, email, hsh=True):
        super(UnconfirmedUser, self).__init__(user_name=user_name, email=email)
        self.hashed_password = bcrypt.generate_password_hash(password) if hsh else password


class UserSchema(ma.Schema):
    class Meta:
        fields = ("id", "user_name", "email")
        model = User


class UnconfirmedUserSchema(ma.Schema):
    class Meta:
        fields = ("id", "user_name", "email")
        model = UnconfirmedUser

