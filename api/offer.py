import jwt
from flask import Blueprint, request, jsonify

from init import limiter, db
from model.offer import Offer, OfferSchema
from util.token import extract_auth_token, decode_token

offer_bp = Blueprint('offer', __name__)
offer_schema = OfferSchema()
offers_schema = OfferSchema(many=True)


@offer_bp.route('/offer', methods=['POST'])
@limiter.limit("10 per minute")
def add_offer():
    try:
        token = extract_auth_token(request)
        if not token:
            raise jwt.InvalidTokenError
        user_id = decode_token(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
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
    location = location.strip()
    phone_number = phone_number.strip()
    offer = Offer(usd_amount=usd_amount, lbp_amount=lbp_amount, usd_to_lbp=usd_to_lbp, user_id=user_id,
                  location=location, phone_number=phone_number)
    db.session.add(offer)
    db.session.commit()
    return jsonify(offer_schema.dump(offer)), 200


@offer_bp.route('/offer/delete', methods=['POST'])
@limiter.limit("10 per minute")
def delete_offer():
    try:
        token = extract_auth_token(request)
        if not token:
            raise jwt.InvalidTokenError
        user_id = decode_token(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return jsonify({"error": "Invalid or expired token"}), 403
    offer_id = request.json.get('offer_id', None)
    if offer_id is None:
        return jsonify({"error": "Missing required fields"}), 400
    offer = Offer.query.get(offer_id)
    if offer is None:
        return jsonify({"error": "Invalid offer input"}), 400
    if offer.user_id != int(user_id):
        return jsonify({"error": "Access is forbidden"}), 403
    db.session.delete(offer)
    db.session.commit()
    return '', 200


@offer_bp.route('/offer/update', methods=['POST'])
@limiter.limit("10 per minute")
def update_offer():
    try:
        token = extract_auth_token(request)
        if not token:
            raise jwt.InvalidTokenError
        user_id = decode_token(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return jsonify({"error": "Invalid or expired token"}), 403
    offer_id = request.json.get('offer_id', None)
    if offer_id is None:
        return jsonify({"error": "Missing required fields"}), 400
    offer = Offer.query.get(offer_id)
    if offer is None:
        return jsonify({"error": "Invalid offer input"}), 400
    if offer.user_id != int(user_id):
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
            offer.usd_amount = usd_amount
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid USD amount, must be a valid number"}), 400
    if lbp_amount is not None:
        try:
            lbp_amount = float(lbp_amount)
            if lbp_amount <= 1e-6:
                return jsonify({"error": "Invalid LBP amount, must be greater than zero"}), 400
            offer.lbp_amount = lbp_amount
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid LBP amount, must be a valid number"}), 400
    if usd_to_lbp is not None:
        try:
            usd_to_lbp = bool(usd_to_lbp)
            offer.usd_to_lbp = usd_to_lbp
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid usd_to_lbp, must be a boolean value"}), 400
    if location is not None:
        location = location.strip()
        offer.location = location
    if phone_number is not None:
        phone_number = phone_number.strip()
        offer.phone_number = phone_number
    db.session.commit()
    return jsonify(offer_schema.dump(offer)), 200
