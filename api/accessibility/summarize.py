import datetime

from flask import Blueprint, request, jsonify

from api.accessibility.ai import summarize_wallet_text, summarize_news_text, summarize_rate_text, summarize_volume_text
from init import limiter, db, tz
from model.news import News
from model.wallet import Wallet, WalletTransaction
from util.accessibility.base import get_period_request, period_to_text
from util.accessibility.summarize import WALLET_TEXT, text_tts, NEWS_TEXT, RATE_TEXT, VOLUME_TEXT
from util.exchange import get_daily_exchange_rate, get_exchange_rate
from util.transaction import get_daily_transaction_volume, get_transaction_volume
from util.user import validate_token

summarize_bp = Blueprint('summarize', __name__, url_prefix='/summarize')


@summarize_bp.route('/rate', methods=['GET'])
@limiter.limit("10 per minute")
def summarize_rate():
    val, start_date, period = get_period_request(request)
    if not val:
        return jsonify({"error": "Invalid or missing period"}), 400
    end_date = datetime.datetime.now(tz)
    rates = []
    while start_date <= end_date:
        usd_to_lbp, lbp_to_usd = get_daily_exchange_rate(start_date) if period != "24h" else get_exchange_rate(
            start_date)
        rates.append(
            {"timestamp": str(start_date.date()) if period != "24h" else start_date.isoformat().replace("+00:00", "Z"),
             "usd_to_lbp": usd_to_lbp,
             "lbp_to_usd": lbp_to_usd})
        start_date += datetime.timedelta(days=1) if period != "24h" else datetime.timedelta(hours=1)
    rt = summarize_rate_text(rates, period_to_text(period))
    msg = RATE_TEXT.format(rt)
    audio, mime = text_tts(msg)
    return jsonify({
        "message": msg,
        "audio": audio,
        "audio_mime_type": mime,
    }), 200


@summarize_bp.route('/volume', methods=['GET'])
@limiter.limit("10 per minute")
def summarize_volume():
    val, start_date, period = get_period_request(request)
    if not val:
        return jsonify({"error": "Invalid or missing period"}), 400
    end_date = datetime.datetime.now(tz)
    volumes = []
    while start_date <= end_date:
        ((usd_to_lbp_total_amount, usd_to_lbp_transaction_count),
         (lbp_to_usd_total_amount, lbp_to_usd_transaction_count)) = get_daily_transaction_volume(start_date) if (
                period != "24h") else (
            get_transaction_volume(start_date, start_date + datetime.timedelta(hours=1)))
        volumes.append(
            {"timestamp": str(start_date.date()) if period != "24h" else start_date.isoformat().replace("+00:00", "Z"),
             "usd_to_lbp": {
                 "total_amount": usd_to_lbp_total_amount,
                 "transaction_count": usd_to_lbp_transaction_count,
             },
             "lbp_to_usd": {
                 "total_amount": lbp_to_usd_total_amount,
                 "transaction_count": lbp_to_usd_transaction_count,
             }})
        start_date += datetime.timedelta(days=1) if period != "24h" else datetime.timedelta(hours=1)
    vl = summarize_volume_text(volumes, period_to_text(period))
    msg = VOLUME_TEXT.format(vl)
    audio, mime = text_tts(msg)
    return jsonify({
        "message": msg,
        "audio": audio,
        "audio_mime_type": mime,
    }), 200


@summarize_bp.route('/wallet', methods=['GET'])
@limiter.limit("10 per minute")
def summarize_wallet():
    val, user = validate_token(request)
    if not val:
        return jsonify({"error": "Invalid or expired token"}), 403
    val, start_date, period = get_period_request(request)
    if not val:
        return jsonify({"error": "Invalid or missing period"}), 400
    wallet = db.session.query(Wallet).filter_by(user_id=user.id).first()
    wallet_transactions = db.session.query(WalletTransaction).filter(
        WalletTransaction.user_id == user.id,
        WalletTransaction.added_date >= start_date
    ).limit(50).all()
    wl = summarize_wallet_text(wallet_transactions, period_to_text(period))
    msg = WALLET_TEXT.format(user.user_name, wallet.usd_amount, wallet.lbp_amount, wl)
    audio, mime = text_tts(msg)
    return jsonify({
        "message": msg,
        "audio": audio,
        "audio_mime_type": mime,
    }), 200


@summarize_bp.route('/news', methods=['GET'])
@limiter.limit("10 per minute")
def summarize_news():
    val, start_date, period = get_period_request(request)
    if not val:
        return jsonify({"error": "Invalid or missing period"}), 400
    news = db.session.query(News).filter(News.timestamp >= start_date).limit(50).all()
    nw = summarize_news_text(news, period_to_text(period))
    msg = NEWS_TEXT.format(nw)
    audio, mime = text_tts(msg)
    return jsonify({
        "message": msg,
        "audio": audio,
        "audio_mime_type": mime,
    }), 200
