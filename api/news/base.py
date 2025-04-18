from flask import Blueprint, jsonify, request

from init import limiter, db
from model.news import NewsSchema, News

news_bp = Blueprint('news', __name__)
news_schema = NewsSchema(many=True)


@news_bp.route('/news', methods=['GET'])
@limiter.limit("10 per minute")
def get_news():
    count = request.args.get('count', '')
    if count:
        try:
            count = int(count)
            if count < 1:
                return jsonify({"error": "Invalid count value, must be greater than 0."}), 400
        except ValueError:
            return jsonify({"error": "Invalid count value, must be a number."}), 400
        news = db.session.query(News).limit(count).all()
    else:
        news = db.session.query(News).all()
    return jsonify(news_schema.dump(news)), 200
