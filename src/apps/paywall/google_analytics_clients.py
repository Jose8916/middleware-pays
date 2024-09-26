from urllib.parse import urljoin

from django.conf import settings
from sentry_sdk import capture_exception, add_breadcrumb, capture_event
import requests
from datetime import date
from dateutil.relativedelta import relativedelta
from ..arcsubs.utils import datetime_to_javadate


def api_request(url, headers, json, method):
    try:
        response = requests.post(url, data=json)
        data = response.json()
    except Exception:
        capture_exception()
    else:
        if response.status_code == 200:
            return data
        else:
            code = data.get('code', '')
            message = data.get('message', 'error')
            extra_data = {
                # 'response': data,
                'method': method,
                'HTTP_code': response.status_code,
                'url': url,
            }
            add_breadcrumb({
                # "ty": "log",
                "level": "info",
                "category": "Request API",
                "message": 'ClientBase.api_request - ARC error {code} "{message}"'.format(
                    code=code, message=message
                ),
                "data": extra_data,  # json.dumps(extra_data, cls=DjangoJSONEncoder),
            })


def send_google_anlytics(category, action, label, event_value, brand, uuid, event):
    if brand == 'gestion':
        tracking_id = settings.UA_GOOGLE_ANALYTICS_GESTION   # 'UA-70251304-40'
    elif brand == 'elcomercio':
        tracking_id = settings.UA_GOOGLE_ANALYTICS_EC  # 'UA-70251304-38'
    data = {
        'v': '1',  # API Version.
        'tid': tracking_id,  # Tracking ID / Property ID.
        'cid': uuid,
        # cid Anonymous Client ID. Ideally, this should be a UUID that
        # is associated with particular user, device, or browser instance.
        't': event,  # Event hit type.
        'ec': category,  # Event category.
        'ea': action,  # Event action.
        'el': uuid,  # Event label.
        'ev': event_value,  # Event value, must be an integer
        'ua': 'Opera/9.80 (Windows NT 6.0) Presto/2.12.388 Version/12.14'
    }

    url = 'https://www.google-analytics.com/collect'
    capture_event(
        {
            'message': 'analitycs',
            'extra': {
                'data': data,
            }
        }
    )
    return api_request(url=url, headers=None, json=data, method='post')


def send_google_anlytics_ecommerce(category, action, label, event_value, brand, uuid, event):
    if brand == 'gestion':
        tracking_id = settings.UA_GOOGLE_ANALYTICS_GESTION
    elif brand == 'elcomercio':
        tracking_id = settings.UA_GOOGLE_ANALYTICS_EC
    data = {
        'v': '1',  # API Version.
        'tid': tracking_id,  # Tracking ID / Property ID.
        'cid': uuid,
        # cid Anonymous Client ID. Ideally, this should be a UUID that
        # is associated with particular user, device, or browser instance.
        't': event,  # Event hit type.
        'ec': category,  # Event category.
        'ea': action,  # Event action.
        'el': label,  # Event label.
        'ev': event_value,  # Event value, must be an integer
        'ua': 'Opera/9.80 (Windows NT 6.0) Presto/2.12.388 Version/12.14'
    }

    url = 'https://www.google-analytics.com/collect'
    capture_event(
        {
            'message': 'analitycs_ecommerce',
            'extra': {
                'data': data,
            }
        }
    )
    return api_request(url=url, headers=None, json=data, method='post')
