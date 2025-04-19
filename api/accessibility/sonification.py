import datetime

from flask import Blueprint, request, jsonify

from api.accessibility.soundgen import delta_to_tone
from init import limiter, tz
from util.accessibility.base import get_period_request
from util.exchange import get_daily_exchange_rate, get_exchange_rate
from util.transaction import get_transaction_volume, get_daily_transaction_volume

sonification_bp = Blueprint('sonification', __name__, url_prefix='/sonification')


@sonification_bp.route('/rate', methods=['GET'])
@limiter.limit("10 per minute")
def summarize_rate():
    val, start_date, period = get_period_request(request)
    if not val:
        return jsonify({"error": "Invalid or missing period"}), 400
    end_date = datetime.datetime.now(tz)
    usd_to_lbp_rates = []
    lbp_to_usd_rates = []
    while start_date <= end_date:
        usd_to_lbp, lbp_to_usd = get_daily_exchange_rate(start_date) if period != "24h" else get_exchange_rate(
            start_date)
        usd_to_lbp_rates.append(usd_to_lbp)
        lbp_to_usd_rates.append(lbp_to_usd)
        start_date += datetime.timedelta(days=1) if period != "24h" else datetime.timedelta(hours=1)
    usd_to_lbp_deltas = []
    for i in range(1, len(usd_to_lbp_rates)):
        usd_to_lbp = usd_to_lbp_rates[i]
        usd_to_lbp_former = usd_to_lbp_rates[i - 1]
        if usd_to_lbp and usd_to_lbp_former:
            usd_to_lbp_delta = 100 * (usd_to_lbp - usd_to_lbp_former) / usd_to_lbp_former
        else:
            usd_to_lbp_delta = None
        usd_to_lbp_deltas.append(usd_to_lbp_delta)
    lbp_to_usd_deltas = []
    for i in range(1, len(lbp_to_usd_rates)):
        lbp_to_usd = lbp_to_usd_rates[i]
        lbp_to_usd_former = lbp_to_usd_rates[i - 1]
        if lbp_to_usd and lbp_to_usd_former:
            lbp_to_usd_delta = 100 * (lbp_to_usd - lbp_to_usd_former) / lbp_to_usd_former
        else:
            lbp_to_usd_delta = None
        lbp_to_usd_deltas.append(lbp_to_usd_delta)
    usd_to_lbp_tones, usd_to_lbp_mime, usd_to_lbp_duration = delta_to_tone(usd_to_lbp_deltas, alpha=100)
    lbp_to_usd_tones, lbp_to_usd_mime, lbp_to_usd_duration = delta_to_tone(lbp_to_usd_deltas, alpha=100)
    return jsonify({
        "usd_to_lbp": {
            "values": usd_to_lbp_deltas,
            "audio": usd_to_lbp_tones,
            "audio_mime": usd_to_lbp_mime,
            "interval": usd_to_lbp_duration
        },
        "lbp_to_usd": {
            "values": lbp_to_usd_deltas,
            "audio": lbp_to_usd_tones,
            "audio_mime": lbp_to_usd_mime,
            "interval": lbp_to_usd_duration
        }
    }), 200


@sonification_bp.route('/volume', methods=['GET'])
@limiter.limit("10 per minute")
def summarize_volume():
    val, start_date, period = get_period_request(request)
    if not val:
        return jsonify({"error": "Invalid or missing period"}), 400
    end_date = datetime.datetime.now(tz)
    usd_to_lbp_total_amounts = []
    lbp_to_usd_total_amounts = []
    while start_date <= end_date:
        ((usd_to_lbp_total_amount, _),
         (lbp_to_usd_total_amount, _)) = get_daily_transaction_volume(start_date) if (
                period != "24h") else (
            get_transaction_volume(start_date, start_date + datetime.timedelta(hours=1)))
        usd_to_lbp_total_amounts.append(usd_to_lbp_total_amount)
        lbp_to_usd_total_amounts.append(lbp_to_usd_total_amount)
        start_date += datetime.timedelta(days=1) if period != "24h" else datetime.timedelta(hours=1)
    usd_to_lbp_deltas = []
    for i in range(1, len(usd_to_lbp_total_amounts)):
        usd_to_lbp = usd_to_lbp_total_amounts[i]
        usd_to_lbp_former = usd_to_lbp_total_amounts[i - 1]
        if usd_to_lbp and usd_to_lbp_former:
            usd_to_lbp_delta = 100 * (usd_to_lbp - usd_to_lbp_former) / usd_to_lbp_former
        else:
            usd_to_lbp_delta = None
        usd_to_lbp_deltas.append(usd_to_lbp_delta)
    lbp_to_usd_deltas = []
    for i in range(1, len(lbp_to_usd_total_amounts)):
        lbp_to_usd = lbp_to_usd_total_amounts[i]
        lbp_to_usd_former = lbp_to_usd_total_amounts[i - 1]
        if lbp_to_usd and lbp_to_usd_former:
            lbp_to_usd_delta = 100 * (lbp_to_usd - lbp_to_usd_former) / lbp_to_usd_former
        else:
            lbp_to_usd_delta = None
        lbp_to_usd_deltas.append(lbp_to_usd_delta)
    usd_to_lbp_tones, usd_to_lbp_mime, usd_to_lbp_duration = delta_to_tone(usd_to_lbp_deltas)
    lbp_to_usd_tones, lbp_to_usd_mime, lbp_to_usd_duration = delta_to_tone(lbp_to_usd_deltas)
    return jsonify({
        "usd_to_lbp": {
            "values": usd_to_lbp_deltas,
            "audio": usd_to_lbp_tones,
            "audio_mime": usd_to_lbp_mime,
            "interval": usd_to_lbp_duration
        },
        "lbp_to_usd": {
            "values": lbp_to_usd_deltas,
            "audio": lbp_to_usd_tones,
            "audio_mime": lbp_to_usd_mime,
            "interval": lbp_to_usd_duration
        }
    }), 200
