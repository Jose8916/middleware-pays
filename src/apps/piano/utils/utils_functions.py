from django.conf import settings
from apps.piano.piano_clients import VXClient
from apps.piano.piano_clients import IDClient
import time
from sentry_sdk import capture_exception, capture_event, push_scope
from datetime import datetime
from django.utils import formats, timezone


def get_start_subscription(app_id):
    # obtiene la fecha de inicio de las suscripciones PIANO
    try:
        tz = timezone.get_current_timezone()
        if app_id == settings.PIANO_APPLICATION_ID['gestion']:
            date_time_obj = datetime.strptime('04/18/2022', '%m/%d/%Y')
        elif app_id == settings.PIANO_APPLICATION_ID['elcomercio']:
            date_time_obj = datetime.strptime('06/15/2022', '%m/%d/%Y')

        return date_time_obj.astimezone(tz)
    except Exception as e:
        print(e)
        return ''


def format_date_start_subscription(subscription):
    """
    tz = pytz.timezone('America/Lima')
    begin_subscription = tz.localize(subscription.starts_date)
    return begin_subscription.strftime("%d-%m-%Y")
    """
    tz = timezone.get_current_timezone()
    tz_date = subscription.start_date.astimezone(tz)
    return formats.date_format(tz_date, "Y-m-d")


def get_data_to_club(subscription):
        data_body = {}
        if subscription.app_id == settings.PIANO_APPLICATION_ID['gestion']:
            brand = 'gestion'
        elif subscription.app_id == settings.PIANO_APPLICATION_ID['elcomercio']:
            brand = 'elcomercio'
        else:
            brand = ''

        subscription_ = VXClient().get_subscription(brand, subscription.subscription_id)
        subscription_dict = subscription_.get('subscription')
        if subscription_dict.get('status') == 'active':
            user_dict = subscription_dict.get('user')
            data = IDClient().get_uid(user_dict.get('uid'), brand)
            user = data.get('user')
            try:
                email_user = user.get('email', '')
            except Exception as e:
                print(e)
                email_user = None

            if email_user:
                document_number = contact_phone = second_last_name = None
                for fields in user.get('custom_fields', ''):
                    if fields.get('fieldName', '') == 'document_type':
                        document_type = fields.get('value', '')
                        inicial = '[\"'
                        final = '\"]'
                        try:
                            document_type = document_type.replace(inicial, "")
                            document_type = document_type.replace(final, "")
                        except Exception as e:
                            print(e)
                            document_type = ''
                    elif fields.get('fieldName', '') == 'document_number':
                        document_number = fields.get('value', '')
                    elif fields.get('fieldName', '') == 'contact_phone':
                        contact_phone = fields.get('value', '')
                    elif fields.get('fieldName', '') == 'second_last_name':
                        second_last_name = fields.get('value', '')

                if document_type in ['OTRO', '']:
                    print(f'2 document_type False: {document_type}')
                    return False

                if document_number and document_type:
                    data_body = {
                        "name": user.get('first_name', ''),
                        "mother_sure_name": second_last_name or '.',
                        "last_name": user.get('last_name', ''),
                        "document_type": document_type,
                        "document_number": document_number,
                        "email": user.get('email', ''),
                        "product_code": "",
                        "package_code": "",
                        "date_initial": format_date_start_subscription(subscription),
                        "date_end": None,
                        "ope_id": None,
                        "ope_id_piano": subscription.subscription_id,
                        "gender": None,
                        "birthdate": None,
                        "telephone": None,
                        "state_recurrent": 1,
                        "program": brand,
                        "origin": "paywall",
                    }

        return data_body


def get_brand(app_id):
    if app_id == settings.PIANO_APPLICATION_ID['gestion']:
        brand = 'gestion'
    elif app_id == settings.PIANO_APPLICATION_ID['elcomercio']:
        brand = 'elcomercio'
    else:
        brand = ''
    return brand


def get_list_amount_payment(data):
    list_price_value = []
    for payment_billing in data.get('payment_billing_plan_table'):
        list_price_value.append(payment_billing.get('priceValue'))
    return list_price_value
