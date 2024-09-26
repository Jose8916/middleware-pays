from datetime import datetime

from django.utils.timezone import get_default_timezone


def timestamp_to_datetime(timestamp):

    if isinstance(timestamp, str):
        timestamp = int(timestamp)

    if isinstance(timestamp, int):
        return datetime.fromtimestamp(
            timestamp / 1000,
            tz=get_default_timezone()
        )


def datetime_to_javadate(_date):

    data = _date.utctimetuple()

    return "{}-{}-{}T{}:{}:{}.000Z".format(*data)


def validation(value):
    try:
        return value
    except Exception:
        return ''

