import phonenumbers
from flask import Blueprint, request, jsonify

from init import limiter, db
from model.dealer import DealerSchema, Dealer
from util.user import validate_token, validate_optional_token

dealer_bp = Blueprint('dealer', __name__, url_prefix='/dealer')
dealer_schema = DealerSchema()
dealers_schema = DealerSchema(many=True)


@dealer_bp.route('/register', methods=['POST'])
@limiter.limit("10 per minute")
def dealer_register():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    if db.session.query(Dealer).filter_by(user_id=user.id).first():
        return jsonify({"error": "Already registered as dealer"}), 400
    lng = request.json.get('lng', None)
    lat = request.json.get('lat', None)
    name = request.json.get('name', None)
    address = request.json.get('address', None)
    rating = request.json.get('rating', None)
    usd_to_lbp = request.json.get('usd_to_lbp', None)
    lbp_to_usd = request.json.get('lbp_to_usd', None)
    phone_number = request.json.get('phone_number', None)
    if (lng is None or lat is None or name is None or address is None or rating is None or
            usd_to_lbp is None or lbp_to_usd is None or phone_number is None):
        return jsonify({"error": "Missing required fields"}), 400
    try:
        lng = float(lng)
        if not ((-180 - 1e-6) <= lng < (180 + 1e-6)):
            return jsonify({"error": "Invalid lng value, must be in [-180, 180)"}), 400
    except (ValueError, ImportError):
        return jsonify({"error": "Invalid lng value, must be a number"}), 400
    try:
        lat = float(lat)
        if not ((-90 - 1e-6) <= lat <= (90 + 1e-6)):
            return jsonify({"error": "Invalid lng value, must be in [-90, 90]"}), 400
    except (ValueError, ImportError):
        return jsonify({"error": "Invalid lng value, must be a number"}), 400
    name = name.strip()
    if not name or len(name) > 128:
        return jsonify({"error": "Invalid name, must be present and less than 128 characters"}), 400
    address = address.strip()
    if not address or len(address) > 128:
        return jsonify({"error": "Invalid address, must be present and less than 128 characters"}), 400
    try:
        rating = float(rating)
        if not (-1e-6 <= rating <= (5 + 1e-6)):
            return jsonify({"error": "Invalid rating, must be between 0 and 5"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid rating, must be between 0 and 5"}), 400
    try:
        usd_to_lbp = float(usd_to_lbp)
        if usd_to_lbp <= 1e-6:
            return jsonify({"error": "Invalid USD-LBP amount, must be greater than zero"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid USD-LBP amount, must be a valid number"}), 400
    try:
        lbp_to_usd = float(lbp_to_usd)
        if lbp_to_usd <= 1e-6:
            return jsonify({"error": "Invalid LBP-USD amount, must be greater than zero"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid LBP-USD amount, must be a valid number"}), 400
    try:
        if not phonenumbers.is_valid_number(phonenumbers.parse(phone_number)):
            return jsonify({"error": "Invalid phone number"}), 400
    except phonenumbers.phonenumberutil.NumberParseException:
        return jsonify({"error": "Invalid phone number"}), 400
    dealer = Dealer(
        lng=lng,
        lat=lat,
        name=name,
        address=address,
        rating=rating,
        usd_to_lbp=usd_to_lbp,
        lbp_to_usd=lbp_to_usd,
        user_id=user.id,
        phone_number=phone_number
    )
    db.session.add(dealer)
    db.session.commit()
    return jsonify(dealer_schema.dump(dealer)), 200


@dealer_bp.route('/unregister', methods=['POST'])
def dealer_unregister():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    dealer = db.session.query(Dealer).filter_by(user_id=user.id).first()
    if not dealer:
        return jsonify({"error": "Not registered as dealer"}), 400
    otp = request.json.get('otp', '')
    if not otp and user.mfa:
        return jsonify({"error": "TOTP Required"}), 401
    elif user.mfa and not user.is_otp_valid(otp):
        return jsonify({"error": "Invalid OTP"}), 403
    db.session.delete(dealer)
    db.session.commit()
    return '', 200


@dealer_bp.route('/update', methods=['POST'])
@limiter.limit("10 per minute")
def dealer_update():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    dealer = db.session.query(Dealer).filter_by(user_id=user.id).first()
    if not dealer:
        return jsonify({"error": "Not registered as dealer"}), 400
    lng = request.json.get('lng', None)
    lat = request.json.get('lat', None)
    name = request.json.get('name', None)
    address = request.json.get('address', None)
    rating = request.json.get('rating', None)
    usd_to_lbp = request.json.get('usd_to_lbp', None)
    lbp_to_usd = request.json.get('lbp_to_usd', None)
    phone_number = request.json.get('phone_number', None)
    if lng:
        try:
            lng = float(lng)
            if not ((-180 - 1e-6) <= lng < (180 + 1e-6)):
                return jsonify({"error": "Invalid lng value, must be in [-180, 180)"}), 400
        except (ValueError, ImportError):
            return jsonify({"error": "Invalid lng value, must be a valid number"}), 400
    if lat:
        try:
            lat = float(lat)
            if not ((-90 - 1e-6) <= lat <= (90 + 1e-6)):
                return jsonify({"error": "Invalid lng value, must be in [-90, 90]"}), 400
        except (ValueError, ImportError):
            return jsonify({"error": "Invalid lng value, must be a valid number"}), 400
    if name:
        name = name.strip()
        if not name or len(name) > 128:
            return jsonify({"error": "Invalid name, must be present and less than 128 characters"}), 400
    if address:
        address = address.strip()
        if not address or len(address) > 128:
            return jsonify({"error": "Invalid address, must be present and less than 128 characters"}), 400
    if rating:
        try:
            rating = float(rating)
            if not (-1e-6 <= rating <= (5 + 1e-6)):
                return jsonify({"error": "Invalid rating, must be between 0 and 5"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid rating, must be a valid number"}), 400
    if usd_to_lbp:
        try:
            usd_to_lbp = float(usd_to_lbp)
            if usd_to_lbp <= 1e-6:
                return jsonify({"error": "Invalid USD-LBP amount, must be greater than zero"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid USD-LBP amount, must be a valid number"}), 400
    if lbp_to_usd:
        try:
            lbp_to_usd = float(lbp_to_usd)
            if lbp_to_usd <= 1e-6:
                return jsonify({"error": "Invalid LBP-USD amount, must be greater than zero"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid LBP-USD amount, must be a valid number"}), 400
    if phone_number:
        try:
            if not phonenumbers.is_valid_number(phonenumbers.parse(phone_number)):
                return jsonify({"error": "Invalid phone number"}), 400
        except phonenumbers.phonenumberutil.NumberParseException:
            return jsonify({"error": "Invalid phone number"}), 400
    if lng:
        dealer.lng = lng
    if lat:
        dealer.lat = lat
    if name:
        dealer.name = name
    if address:
        dealer.address = address
    if rating:
        dealer.rating = rating
    if usd_to_lbp:
        dealer.usd_to_lbp = usd_to_lbp
    if lbp_to_usd:
        dealer.lbp_to_usd = lbp_to_usd
    if phone_number:
        dealer.phone_number = phone_number
    db.session.commit()
    return jsonify(dealer_schema.dump(dealer)), 200


@dealer_bp.route('', methods=['GET'])
@limiter.limit("10 per minute")
def dealer_get():
    val, user = validate_optional_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    dealer_id = request.args.get('id', '')
    if not dealer_id and not user:
        return jsonify({"error": "Missing required fields"}), 400
    if not dealer_id and user:
        dealer = db.session.query(Dealer).filter_by(user_id=user.id).first()
        if not dealer:
            return jsonify({"error": "Not registered as dealer"}), 400
    else:
        dealer = db.session.query(Dealer).filter_by(id=dealer_id).first()
        if not dealer:
            return jsonify({"error": "Invalid dealer specified"}), 400
    return jsonify(dealer_schema.dump(dealer)), 200


@dealer_bp.route('/all', methods=['GET'])
@limiter.limit("10 per minute")
def dealers_get():
    dealers = db.session.query(Dealer).all()
    return jsonify(dealers_schema.dump(dealers)), 200
