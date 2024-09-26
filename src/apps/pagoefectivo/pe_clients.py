from urllib.parse import urljoin

from django.conf import settings
from sentry_sdk import capture_exception, add_breadcrumb, capture_event
import requests
from datetime import date
from dateutil.relativedelta import relativedelta
from ..arcsubs.utils import datetime_to_javadate
from apps.pagoefectivo.constants import test


class ClientBase(object):

    def api_request(self, url, method, *arg, **kwarks):
        try:
            response = getattr(requests, method)(url, *arg, **kwarks)
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


class PESalesClient(object):
    """
        docstring for SalesClient
    """
    def document_type(self, user_document_type):
        if user_document_type in ['RUC', 'CEX', 'CDI']:
            document_type = 'NAN'
        else:
            document_type = user_document_type
        return document_type

    def create_cip(self, cip_obj, cd, date_expiry, token):
        if cip_obj.plan.partner.partner_code == 'elcomercio':
            service_id = settings.SERVICE_ID_EC
        elif cip_obj.plan.partner.partner_code == 'gestion':
            service_id = settings.SERVICE_ID_GESTION

        headers = {
            'Authorization': 'Bearer ' + token,
            'Origin': 'web',
            'Accept-Language': 'es-PE',
            'Content-Type': 'application/json'
        }

        last_name = '{} {}'.format(cd.get('lastname_father', ''), cd.get('lastname_mother', ''))
        last_name = last_name.strip()

        payload = {
            "currency": cd.get('currency', ''),
            "amount": float(cd.get('amount', '')),
            "transactionCode": cip_obj.id,
            "adminEmail": settings.EMAIL_ADMIN_PEFECTIVO,
            "dateExpiry": date_expiry,
            "paymentConcept": cd.get('payment_concept', ''),
            "additionalData": cd.get('additional_data', ''),
            "userEmail": cd.get('user_email', ''),
            "userId": cd.get('user_id', ''),
            "userName": cd.get('user_name', ''),
            "userLastName": last_name,
            "userDocumentType": self.document_type(cd.get('user_document_type', '')),
            "userDocumentNumber": cd.get('user_document_number', ''),
            "userPhone": cd.get('user_phone', ''),
            "userCodeCountry": cd.get('user_code_country', ''),
            "serviceId": service_id  # 1290
        }
        url = urljoin(
            settings.DOMAIN_PAGO_EFECTIVO,
            "/v1/cips",
        )

        try:
            response = requests.post(url, headers=headers, json=payload)
        except Exception as e:
            capture_event(
                {
                    'message': e,
                    'extra': {
                        'data': payload,
                    }
                }
            )

            dict_fields = {
                "message": str(e),
                "status": False,
                "response": '',
                "body": payload
            }
            return None, dict_fields
        else:
            if (response.status_code <= 299) and (response.status_code >= 200):
                dict_fields = {
                    "httpStatus": 200,
                    "message": "Se registro correctamente",
                    "status": True,
                    "response": response.json(),
                    "body": payload
                }
                return response, dict_fields
            elif response.status_code == 401:
                dict_fields = {
                    "httpStatus": response.status_code,
                    "message": "Error de permisos",
                    "status": False,
                    "response": response.json() if response.text else '',
                    "body": payload
                }
                return response, dict_fields
            else:
                capture_event(
                    {
                        'message': 'Error',
                        'extra': {
                            'envio': payload,
                            'response': response.text,
                        }
                    }
                )
                return None

