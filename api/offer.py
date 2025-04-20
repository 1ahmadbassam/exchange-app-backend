import phonenumbers
from flask import Blueprint, request, jsonify

from init import limiter, db
from model.offer import Offer, OfferSchema
from model.transaction import Transaction
from model.wallet import Wallet
from util.user import validate_token
from util.wallet import add_two_way_wallet_transaction

offer_bp = Blueprint('offer', __name__, url_prefix='/offer')
offer_schema = OfferSchema()
offers_schema = OfferSchema(many=True)


@offer_bp.route('', methods=['POST'])
@limiter.limit("10 per minute")
def add_offer():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    usd_amount = request.json.get('usd_amount', None)
    lbp_amount = request.json.get('lbp_amount', None)
    usd_to_lbp = request.json.get('usd_to_lbp', None)
    location = request.json.get('location', None)
    phone_number = request.json.get('phone_number', None)
    if usd_amount is None or lbp_amount is None or usd_to_lbp is None or location is None or phone_number is None:
        return jsonify({"error": "Missing required fields"}), 400
    try:
        usd_amount = float(usd_amount)
        if usd_amount <= 1e-6:
            return jsonify({"error": "Invalid USD amount, must be greater than zero"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid USD amount, must be a valid number"}), 400
    try:
        lbp_amount = float(lbp_amount)
        if lbp_amount <= 1e-6:
            return jsonify({"error": "Invalid LBP amount, must be greater than zero"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid LBP amount, must be a valid number"}), 400
    try:
        usd_to_lbp = bool(usd_to_lbp)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid usd_to_lbp, must be a boolean value"}), 400
    phone_number = phone_number.strip()
    try:
        if not phonenumbers.is_valid_number(phonenumbers.parse(phone_number)):
            return jsonify({"error": "Invalid phone number"}), 400
    except phonenumbers.phonenumberutil.NumberParseException:
        return jsonify({"error": "Invalid phone number"}), 400
    location = location.strip()
    if not location or len(location) > 128:
        return jsonify({"error": "Invalid location, must be present and less than 128 characters"}), 400
    wallet = db.session.query(Wallet).filter_by(user_id=user.id).first()
    if usd_to_lbp and not wallet.has_enough_usd(-usd_amount):
        return jsonify({"error": "Not enough USD in wallet. Add more USD before attempting this transaction."}), 401
    elif not usd_to_lbp and not wallet.has_enough_lbp(-lbp_amount):
        return jsonify({"error": "Not enough LBP in wallet. Add more LBP before attempting this transaction."}), 401
    offer = Offer(usd_amount=usd_amount, lbp_amount=lbp_amount, usd_to_lbp=usd_to_lbp, user_id=user.id,
                  location=location, phone_number=phone_number)
    wallet.add_inflight(usd_amount, lbp_amount, usd_to_lbp)
    db.session.add(offer)
    db.session.commit()
    return jsonify(offer_schema.dump(offer)), 200


@offer_bp.route('/delete', methods=['POST'])
@limiter.limit("10 per minute")
def delete_offer():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    offer_id = request.json.get('id', None)
    if offer_id is None:
        return jsonify({"error": "Missing required fields"}), 400
    offer = db.session.query(Offer).filter_by(id=offer_id).first()
    if not offer:
        return jsonify({"error": "Invalid offer input"}), 400
    if offer.user_id != int(user.id):
        return jsonify({"error": "Access is forbidden"}), 403
    if offer.available:
        wallet = db.session.query(Wallet).filter_by(user_id=user.id).first()
        wallet.remove_inflight(offer.usd_amount, offer.lbp_amount, offer.usd_to_lbp)
    db.session.delete(offer)
    db.session.commit()
    return '', 200


@offer_bp.route('/update', methods=['POST'])
@limiter.limit("10 per minute")
def update_offer():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    offer_id = request.json.get('id', None)
    if offer_id is None:
        return jsonify({"error": "Missing required fields"}), 400
    offer = db.session.query(Offer).filter_by(id=offer_id).first()
    if not offer:
        return jsonify({"error": "Invalid offer input"}), 400
    if offer.user_id != int(user.id):
        return jsonify({"error": "Access is forbidden"}), 403
    usd_amount = request.json.get('usd_amount', None)
    lbp_amount = request.json.get('lbp_amount', None)
    usd_to_lbp = request.json.get('usd_to_lbp', None)
    location = request.json.get('location', None)
    phone_number = request.json.get('phone_number', None)
    if usd_amount is not None:
        try:
            usd_amount = float(usd_amount)
            if usd_amount <= 1e-6:
                return jsonify({"error": "Invalid USD amount, must be greater than zero"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid USD amount, must be a valid number"}), 400
    if lbp_amount is not None:
        try:
            lbp_amount = float(lbp_amount)
            if lbp_amount <= 1e-6:
                return jsonify({"error": "Invalid LBP amount, must be greater than zero"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid LBP amount, must be a valid number"}), 400
    if usd_to_lbp is not None:
        try:
            usd_to_lbp = bool(usd_to_lbp)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid usd_to_lbp, must be a boolean value"}), 400
    else:
        usd_to_lbp = offer.usd_to_lbp
    wallet = db.session.query(Wallet).filter_by(user_id=user.id).first()
    if usd_amount and usd_to_lbp is True and not wallet.has_enough_usd(-usd_amount, offer.usd_amount):
        return jsonify({"error": "Not enough USD in wallet. Add more USD before attempting this transaction."}), 401
    if lbp_amount and usd_to_lbp is False and not wallet.has_enough_lbp(-lbp_amount, offer.lbp_amount):
        return jsonify({"error": "Not enough LBP in wallet. Add more LBP before attempting this transaction."}), 401
    if location is not None:
        location = location.strip()
        if not location or len(location) > 128:
            return jsonify({"error": "Invalid location, must be present and less than 128 characters"}), 400
    if phone_number is not None:
        phone_number = phone_number.strip()
        try:
            if not phonenumbers.is_valid_number(phonenumbers.parse(phone_number)):
                return jsonify({"error": "Invalid phone number"}), 400
        except phonenumbers.phonenumberutil.NumberParseException:
            return jsonify({"error": "Invalid phone number"}), 400
    # update inflight
    wallet.remove_inflight(offer.usd_amount, offer.lbp_amount, offer.usd_to_lbp)
    if usd_amount:
        offer.usd_amount = usd_amount
    if lbp_amount:
        offer.lbp_amount = lbp_amount
    offer.usd_to_lbp = usd_to_lbp
    wallet.add_inflight(usd_amount if usd_amount is not None else offer.usd_amount,
                        lbp_amount if lbp_amount is not None else offer.lbp_amount, usd_to_lbp)
    if location:
        offer.location = location
    if phone_number:
        offer.phone_number = phone_number
    db.session.commit()
    return jsonify(offer_schema.dump(offer)), 200


@offer_bp.route('/available', methods=['GET'])
@limiter.limit("10 per minute")
def get_available_offers():
    offers = db.session.query(Offer).filter_by(available=True).all()
    return jsonify(offers_schema.dump(offers)), 200


@offer_bp.route('/my', methods=['GET'])
@limiter.limit("10 per minute")
def get_my_offers():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    offers = db.session.query(Offer).filter_by(user_id=user.id).all()
    return jsonify(offers_schema.dump(offers)), 200


@offer_bp.route('/accept', methods=['POST'])
@limiter.limit("10 per minute")
def accept_offer():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    offer_id = request.json.get('id', None)
    if offer_id is None:
        return jsonify({"error": "Missing required fields"}), 400
    offer = db.session.query(Offer).filter_by(id=offer_id).first()
    if not offer:
        return jsonify({"error": "Invalid offer input"}), 400
    if offer.user_id == int(user.id):
        return jsonify({"error": "Invalid offer input - cannot accept own offer"}), 400
    wallet = db.session.query(Wallet).filter_by(user_id=user.id).first()
    if offer.usd_to_lbp and not wallet.has_enough_usd(-offer.usd_amount):
        return jsonify({"error": "Not enough USD in wallet. Add more USD before accepting this transaction."}), 401
    elif not offer.usd_to_lbp and not wallet.has_enough_lbp(-offer.lbp_amount):
        return jsonify({"error": "Not enough LBP in wallet. Add more LBP before accepting this transaction."}), 401
    # restore loss to original user
    original_wallet = db.session.query(Wallet).filter_by(user_id=offer.user_id).first()
    original_wallet.remove_inflight(offer.usd_amount, offer.lbp_amount, offer.usd_to_lbp)
    offer.available = False
    transaction = Transaction(usd_amount=offer.usd_amount, lbp_amount=offer.lbp_amount, usd_to_lbp=offer.usd_to_lbp,
                              user_id=user.id, offer=True)
    db.session.add(transaction)
    db.session.commit()
    add_two_way_wallet_transaction(transaction, offer.user_id)
    return jsonify(offer_schema.dump(offer)), 200
