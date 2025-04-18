import datetime
import random

from dateutil.relativedelta import relativedelta
from sqlalchemy import func

from init import app, db, bcrypt, tz
from model.transaction import Transaction
from model.user import User
from model.wallet import WalletTransaction
from model.accessibility import Accessibility

const_pass = bcrypt.generate_password_hash("123")


def generate_user(user_name):
    user = User(user_name=user_name, password=const_pass, email=user_name, hsh=False)
    db.session.add(user)
    db.session.commit()
    # force accessibility table to get parsed
    accessibility = db.session.query(Accessibility).filter_by(user_id=user.id).first()
    if not accessibility:
        raise ValueError("Accessibility not found")


def generate_transaction(added_date):
    usd_amount = random.randint(1, 50000)
    lbp_amount = int(usd_amount * random.uniform(80000, 100000) / 1000) * 1000
    usd_to_lbp = random.choice([True, False])
    user_id = random.randint(1, 5000)

    return (Transaction(usd_amount=usd_amount,
                        lbp_amount=lbp_amount,
                        usd_to_lbp=usd_to_lbp,
                        user_id=user_id,
                        added_date=added_date),
            WalletTransaction(usd_amount=50000,
                              lbp_amount=5000000000,
                              user_id=user_id,
                              description="Deposit",
                              added_date=added_date)
            )


def populate_transactions(database, period="2yr"):
    today = datetime.datetime.now(tz)
    if period == "24h":
        past = today - datetime.timedelta(hours=24)
    elif period == "7d":
        past = today - datetime.timedelta(days=7)
    elif period == "30d":
        past = today - datetime.timedelta(days=30)
    elif period == "3mon":
        past = today - relativedelta(months=3)
    elif period == "6mon":
        past = today - relativedelta(months=6)
    elif period == "1yr":
        past = today - relativedelta(years=1)
    elif period == "2yr":
        past = today - relativedelta(years=2)
    else:
        raise ValueError("Unrecognized period, valid values are: 24h, 7d, 30d, 3mon, 6mon, 1yr, 2yr")
    cur = today - datetime.timedelta(days=1)
    full = (cur - past).days
    dt = 0
    wu = False
    while cur >= past:
        for _ in range(random.randint(30, 50)):
            cur = cur.replace(hour=random.randint(8, 20), minute=random.randint(0, 59), second=random.randint(0, 59),
                              microsecond=random.randint(0, 999999))
            transaction, wt = generate_transaction(cur)
            database.session.add(wt)
            database.session.commit()
            database.session.add(transaction)
        cur = cur - datetime.timedelta(days=1)
        dt += 1
        if dt % 10 == 0:
            print(f"Progress: {int(100 * dt / full)}/100%")
            if int(100 * dt / full) == 100:
                wu = True
    database.session.commit()
    if not wu:
        print(f"Progress: 100/100%")
    cur = today
    if today.hour >= 8:
        for _ in range(random.randint(30, 50)):
            h = random.randint(8, today.hour)
            if h == today.hour:
                m = random.randint(0, today.minute)
            else:
                m = random.randint(0, 59)
            # no need to worry about second/millisecond increments
            cur = cur.replace(hour=h, minute=m, second=random.randint(0, 59), microsecond=random.randint(0, 999999))
            transaction, wt = generate_transaction(cur)
            database.session.add(wt)
            database.session.commit()
            database.session.add(transaction)
        database.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        max_id = db.session.query(func.max(User.id)).scalar()
        for i in range(max_id + 1 if max_id else 1, 5001):
            generate_user(f"_genuser{i}")
        populate_transactions(db, "2yr")
