import datetime

import pyotp
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from init import app, db, ma, bcrypt, tz


class User(db.Model):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    mfa: Mapped[bool] = mapped_column(nullable=False, default=False)
    mfa_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    password_updated: Mapped[datetime.datetime] = mapped_column(nullable=False)

    def __init__(self, user_name, password, email, hsh=True):
        super(User, self).__init__(user_name=user_name, email=email, password_updated=datetime.datetime.now(tz))
        self.hashed_password = bcrypt.generate_password_hash(password) if hsh else password
        self.mfa_code = pyotp.random_base32()

    def update_password(self, password, hsh=True):
        self.hashed_password = bcrypt.generate_password_hash(password) if hsh else password
        self.password_updated=datetime.datetime.now(tz)

    def can_change_password(self):
        return datetime.datetime.now(tz) - self.password_updated.replace(tzinfo=tz) >= datetime.timedelta(hours=1)

    def get_authentication_setup_uri(self):
        return pyotp.totp.TOTP(self.mfa_code).provisioning_uri(
            name=self.email, issuer_name=app.config['APP_NAME'])

    def is_otp_valid(self, user_otp):
        totp = pyotp.parse_uri(self.get_authentication_setup_uri())
        return totp.verify(user_otp)


class UnconfirmedUser(db.Model):
    __tablename__ = 'unconfirmed_user'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    password_updated: Mapped[datetime.datetime] = mapped_column(nullable=False)

    def __init__(self, user_name, password, email, hsh=True):
        super(UnconfirmedUser, self).__init__(user_name=user_name, email=email, password_updated=datetime.datetime.now(tz))
        self.hashed_password = bcrypt.generate_password_hash(password) if hsh else password

    def update_password(self, password, hsh=True):
        self.hashed_password = bcrypt.generate_password_hash(password) if hsh else password
        self.password_updated=datetime.datetime.now(tz)

    def can_change_password(self):
        return datetime.datetime.now(tz) - self.password_updated.replace(tzinfo=tz) >= datetime.timedelta(hours=1)


class UserSchema(ma.Schema):
    class Meta:
        fields = ("id", "user_name", "email")
        model = User


class UnconfirmedUserSchema(ma.Schema):
    class Meta:
        fields = ("user_name", "email")
        model = UnconfirmedUser

