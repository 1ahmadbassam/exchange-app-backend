from api.accessibility import accessibility_bp
from api.dealer import dealer_bp
from api.exchange import exchange_bp
from api.offer import offer_bp
from api.transaction import transaction_bp
from api.user.base import user_bp
from api.user.internal import user_internal_bp
from api.user.mfa import user_mfa_bp
from api.wallet import wallet_bp
from init import app, db

app.register_blueprint(user_bp)
app.register_blueprint(user_internal_bp)
app.register_blueprint(user_mfa_bp)
app.register_blueprint(transaction_bp)
app.register_blueprint(exchange_bp)
app.register_blueprint(offer_bp)
app.register_blueprint(wallet_bp)
app.register_blueprint(dealer_bp)
app.register_blueprint(accessibility_bp)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=False)
