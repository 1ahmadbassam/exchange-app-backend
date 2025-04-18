from flask import Blueprint, request, jsonify

from init import limiter, db
from model.accessibility import AccessibilitySchema, Accessibility
from util.user import validate_token

accessibility_bp = Blueprint('accessibility', __name__)
accessibility_schema = AccessibilitySchema()


@accessibility_bp.route('/accessibility', methods=['GET'])
@limiter.limit("10 per minute")
def get_accessibility():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    accessibility = db.session.query(Accessibility).filter_by(user_id=user.id).first()
    return jsonify(accessibility_schema.dump(accessibility)), 200


@accessibility_bp.route('/accessibility', methods=['POST'])
@limiter.limit("10 per minute")
def set_accessibility():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    inverted_colors = request.json.get('inverted_colors', False)
    sonification = request.json.get('sonification', False)
    narration = request.json.get('narration', False)
    try:
        inverted_colors = bool(inverted_colors)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid value for inverted_colors, must be a boolean"}), 400
    try:
        sonification = bool(sonification)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid value for sonification, must be a boolean"}), 400
    try:
        narration = bool(narration)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid value for narration, must be a boolean"}), 400
    accessibility = db.session.query(Accessibility).filter_by(user_id=user.id).first()
    accessibility.inverted_colors = inverted_colors
    accessibility.sonification = sonification
    accessibility.narration = narration
    db.session.commit()
    return jsonify(accessibility_schema.dump(accessibility)), 200
