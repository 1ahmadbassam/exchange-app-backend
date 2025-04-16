from init import db
from model.wallet import WalletTransaction


def add_two_way_wallet_transaction(transaction, other_id):
    # the transaction only works in the original way for the offer owner
    wl = WalletTransaction(usd_amount=-transaction.usd_amount if transaction.usd_to_lbp else transaction.usd_amount,
                           lbp_amount=transaction.lbp_amount if transaction.usd_to_lbp else -transaction.lbp_amount,
                           user_id=other_id,
                           added_date=transaction.added_date,
                           description="USD to LBP exchange" if transaction.usd_to_lbp else "LBP to USD exchange")
    # otherwise, flip. e.g. if the owner listed an usd_to_lbp transaction, then he is selling me USD in exchange for my lbp
    wl2 = WalletTransaction(usd_amount=transaction.usd_amount if transaction.usd_to_lbp else -transaction.usd_amount,
                            lbp_amount=-transaction.lbp_amount if transaction.usd_to_lbp else transaction.lbp_amount,
                            user_id=transaction.user_id,
                            added_date=transaction.added_date,
                            description="LBP to USD exchange" if transaction.usd_to_lbp else "USD to LBP exchange")
    db.session.add(wl)
    db.session.add(wl2)
    db.session.commit()
