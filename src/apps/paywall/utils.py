from datetime import date, datetime, timedelta
import random
import string

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, validate_email
from django.utils.timezone import get_default_timezone
from sentry_sdk import capture_exception


def current_time():
    berlin_now = datetime.now(get_default_timezone())
    return berlin_now


def sort_dictionary_list_by_key(list_dict, type_order):
    """Sort ascending or descending a list of parameters by a key

    Parameters
    ----------
    list_dict : list
        This is a list of dictionaries

    type_order : string
        Can take the values ascendant or falling

    Returns
    -------
    list
        a list of dictionaries ordered
    """
    try:
        return sorted(lis, key=lambda i: i['age'], reverse=True)
    except Exception as e:
        return []


def utc_to_lima_time_zone(date_utc):
    if not date_utc:
        return

    try:
        result = get_default_timezone().localize(
            datetime.strptime(date_utc, "%Y-%m-%d %H:%M:%S")
        )

    except Exception:
        capture_exception()

    else:
        return result


# def get_profile_user_arc(token, site):
#     """
#         token: json web token arc
#     """
#     # dict_sites = {
#     #     'elcomercio': settings.PUBLIC_ARC_DOMAIN_COMERCIO,
#     #     'gestion': settings.PUBLIC_ARC_DOMAIN_GESTION
#     # }

#     try:
#         headers = {
#             'Content-Type': 'application/json',
#             'Authorization': '%s' % token,
#         }
#         if site:
#             url = settings.PAYWALL_ARC_PUBLIC_URL.format(site=site) + '/identity/public/v1/profile'
#             response = requests.get(url, headers=headers)
#             return response.json()
#         else:
#             return {}
#     except Exception as e:
#         print(e)
#         print('no se encontro al usuario en arc')
#         return ''


def is_email(string):
    validator = EmailValidator()
    try:
        validator(string)

    except ValidationError:
        return False

    else:
        return True


def random_characters(stringLength=6):
    lettersAndDigits = string.ascii_lowercase + string.digits
    return ''.join(random.choice(lettersAndDigits) for i in range(stringLength))


def day_today():
    today = date.today()
    return today


def sum_days(cantidad, day=None):
    if not day:
        day = current_time()
    day_time = day + timedelta(days=int(cantidad))
    return day_time.strftime("%Y-%m-%d %H:%M:%S")


def validar_email(email):
    try:
        validate_email(email)

    except Exception:
        return False

    else:
        return True

















