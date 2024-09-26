from datetime import date, datetime, timedelta
from django.utils.timezone import get_default_timezone
from sentry_sdk import capture_exception


def get_yesterday():
    today = date.today()
    oneday = timedelta(days=1)
    yesterday = today - oneday
    return yesterday
