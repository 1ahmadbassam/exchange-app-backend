import datetime

from init import tz


def get_period_request(request):
    period = request.args.get("period", "").strip()
    if not period:
        return False, None, None
    today = datetime.datetime.now(tz)
    if period == "24h":
        former_date = today - datetime.timedelta(hours=24)
    elif period == "7d":
        former_date = today - datetime.timedelta(days=7)
    elif period == "14d":
        former_date = today - datetime.timedelta(days=14)
    elif period == "30d":
        former_date = today - datetime.timedelta(days=30)
    else:
        return False, None, None
    return True, former_date, period


def period_to_text(period):
    if period == "24h":
        return "24 hours"
    elif period == "7d":
        return "7 days"
    elif period == "14d":
        return "14 days"
    elif period == "30d":
        return "30 days"
    else:
        return period
