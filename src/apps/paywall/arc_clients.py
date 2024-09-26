from urllib.parse import urljoin

from django.conf import settings
from sentry_sdk import capture_exception, add_breadcrumb, capture_event
import requests
from datetime import date
from dateutil.relativedelta import relativedelta
from ..arcsubs.utils import datetime_to_javadate


class ClientBase(object):

    def api_request(self, url, method, *arg, **kwarks):
        try:
            response = getattr(requests, method)(url, *arg, **kwarks)
            data = response.json()
        except Exception as e:
            print(e)
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

    def api_request_v2(self, url, method, *arg, **kwarks):
        try:
            response = getattr(requests, method)(url, *arg, **kwarks)
            data = response.json()
        except Exception as e:

            capture_exception()
        else:
            if response.status_code == 200:
                return data
            else:
                return []


class IdentityClient(ClientBase):

    def get_profile(self, identify):
        if '@' in identify:
            raise Exception('get_user_by_email error')
        else:
            return self.get_profile_by_uuid(identify)

    def get_profile_by_uuid(self, uuid):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + settings.PAYWALL_ARC_TOKEN
        }

        url = urljoin(
            settings.PAYWALL_ARC_URL,
            '/identity/api/v1/profile/{uuid}'.format(uuid=uuid),
        )

        add_breadcrumb({
            # "ty": "log",
            "level": "info",
            "category": "IdentityClient",
            "message": 'get_profile_by_uuid',
            "data": {'uuid': str(uuid), },
        })
        return self.api_request(url=url, headers=headers, method='get')

    def update_profile_by_uuid(self, uuid, email):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + settings.PAYWALL_ARC_TOKEN
        }

        url = urljoin(
            settings.PAYWALL_ARC_URL,
            '/identity/api/v1/profile/{uuid}'.format(uuid=uuid),
        )
        data = self.get_profile_by_uuid(uuid)

        if data:
            data['email'] = email
            # return self.api_request(url=url, method='put', headers=headers, data=data)
            try:
                response = requests.put(url, headers=headers, json=data)
                response_data = response.json()
            except Exception as e:
                capture_exception()
            else:
                if response.status_code == 200:
                    return response_data
                else:
                    capture_event(
                        {
                            'message': 'Error al actualizar el perfil',
                            'extra': {
                                'url': url,
                                'response': response,
                                'data': data
                            }
                        }
                    )
        else:
            capture_event(
                {
                    'message': 'No existe el usuario',
                    'extra': {
                        'uuid': uuid,
                        'user': data
                    }
                }
            )
            return 0

    def get_profile_by_token(self, site, token):
        headers = {
            'Content - Type': 'application / json',
            'Authorization': 'Bearer ' + token
        }

        url = urljoin(
            settings.PAYWALL_ARC_PUBLIC_URL.format(site=site),
            '/identity/public/v1/profile',
        )

        add_breadcrumb(
            level="info",
            category="Request API",
            message='IdentityClient.get_profile_by_token site [{site}]'.format(site=site),
            data={
                'site': site,
                'token': token,
            },
        )
        return self.api_request(url=url, headers=headers, method='get')

    def change_password(self, uuid, password):
        headers = {
            'Content - Type': 'application / json',
            'Authorization': 'Bearer ' + settings.PAYWALL_ARC_TOKEN,
            # 'Arc-Site': site
        }

        data = {
            'oldPassword': "",
            'newPassword': password
        }

        url = urljoin(
            settings.PAYWALL_ARC_URL,
            '/identity/api/v1/password/{uuid}'.format(uuid=uuid),
        )

        return self.api_request(url=url, headers=headers, json=data, method='put')


class SalesClient(ClientBase):
    """
        docstring for SalesClient
    """

    def get_subscription(self, site, subscription_id):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + settings.PAYWALL_ARC_TOKEN,
            'Arc-Site': site
        }

        url = '{api}/sales/api/v1/subscription/{subscriptionID}/details'.format(
            api=settings.PAYWALL_ARC_URL,
            subscriptionID=subscription_id
        )

        add_breadcrumb({
            # "ty": "log",
            "level": "info",
            "category": "SalesClient",
            "message": 'get_subscription',
            "data": {
                'site': site,
                'subscription_id': subscription_id,
            },
        })
        return self.api_request_v2(url=url, headers=headers, method='get')

    def get_order(self, site, order_id):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + settings.PAYWALL_ARC_TOKEN,
            'Arc-Site': site
        }

        url = '{api}/sales/api/v1/order/detail/{orderNumber}'.format(
            api=settings.PAYWALL_ARC_URL,
            orderNumber=order_id
        )

        return self.api_request(url=url, headers=headers, method='get')

    def get_campaign(self, site, name):
        headers = {
            'Content-Type': 'application/json',
        }

        url = '{api}/retail/public/v1/offer/preview/{campaignName}'.format(
            api=settings.PAYWALL_ARC_PUBLIC_URL.format(site=site),
            campaignName=name
        )

        return self.api_request(url=url, headers=headers, method='get')

    def link_subscription(self, client_id, sku, price_code, token, expiration):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + settings.PAYWALL_ARC_TOKEN,
        }

        data = {
            "sku": sku,
            "priceCode": price_code,
            "token": str(token),
            "expirationDateUTC": datetime_to_javadate(expiration),
            "clientId": str(client_id),
        }

        url = urljoin(
            settings.PAYWALL_ARC_URL,
            '/sales/api/v1/subscription/link',
        )

        add_breadcrumb({
            # "ty": "log",
            "level": "info",
            "category": "SalesClient",
            "message": 'link_subscription',
            "data": {
                'client_id': str(client_id),
                'sku': sku,
                'price_code': price_code,
                'token': token,
                'expiration': str(expiration),
            },
        })
        return self.api_request(url=url, headers=headers, json=data, method='post')

    def unlink_subscription(self, client_id, sku, price_code, token, expiration):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + settings.PAYWALL_ARC_TOKEN,
        }

        data = {
            "sku": sku,
            "priceCode": price_code,
            "token": token,
            "expirationDateUTC": expiration.strftime("%Y-%m-%dT%H:%M:%S"),
            "clientId": client_id
        }

        url = urljoin(
            settings.PAYWALL_ARC_URL,
            '/sales/api/v1/subscription/link/revoke',
        )

        return self.api_request(url=url, headers=headers, json=data, method='put')

    def has_a_refund(self, site, arc_order):
        # valida si la orden se le a realizado una devolucion

        refund_obj = self.get_order(site=site, order_id=arc_order)
        try:
            for pay in refund_obj['payments']:
                for transaction in pay['financialTransactions']:
                    if transaction['transactionType'] == 'Refund':
                        return True
        except Exception:
            return True
        return False

    def has_a_refund_operation(self, site, arc_order):
        # valida si la orden se le a realizado una devolucion

        refund_obj = self.get_order(site=site, order_id=arc_order)
        for pay in refund_obj['payments']:
            for transaction in pay['financialTransactions']:
                if transaction['transactionType'] == 'Refund':
                    return True
        return False

class ReportClient(ClientBase):
    """
        docstring for ReportClient
    """

    def get_sales(self, jobid, site):
        url = '{domain}sales/api/v1/report/{jobid}/download'.format(
            domain=settings.PAYWALL_ARC_URL,
            jobid=jobid
        )

        headers = {
            'Content-Type': "application/json",
            'Authorization': "Bearer " + settings.PAYWALL_ARC_TOKEN,
            'cache-control': "no-cache",
            'Arc-Site': '' + str(site)
        }
        return self.api_request_v2(url=url, headers=headers, method='get')

    def report_post(self, start_date, end_date, site, report_type):
        headers = {
            'content-type': 'application/json',
            'Authorization': 'Bearer ' + settings.PAYWALL_ARC_TOKEN,
            'Arc-Site': '' + str(site)
        }

        payload = {
            "name": "financial_transactions_report",
            "startDate": start_date + "T00:00:00.000Z",
            "endDate": end_date + "T00:00:00.000Z",
            "reportType": report_type,
            "reportFormat": "json"
        }
        url = urljoin(settings.PAYWALL_ARC_URL, '/sales/api/v1/report/schedule')
        try:
            response = requests.post(url, json=payload, headers=headers)
            result = response.json()
            result['payload'] = payload
            return result

        except Exception as e:
            print(e)
            return ""


class SaleLinked(object):
    site = ''
    headers = {}
    url = None

    def __init__(self, site):
        self.connect(site)
        self.site = site

    def create(self, token, uuid, price_code, sku):
        expiration_date = date.today() + relativedelta(years=100)
        payload = {
            "sku": sku,
            "priceCode": price_code,
            "token": str(token),
            "expirationDateUTC": expiration_date.strftime("%Y-%m-%dT%H:%M:%S") + '.000Z',
            "clientId": str(uuid)
        }

        url = self.url + 'sales/api/v1/subscription/link'

        try:
            response = requests.post(url, headers=self.headers, json=payload)
        except Exception as e:
            capture_event(
                {
                    'message': 'error en subscription link',
                    'extra': {
                        'data': payload,
                        'respuesta': str(e)
                    }
                }
            )

            dict_fields = {
                "message": str(e),
                "status": False,
                "response": str(e),
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

            else:
                dict_fields = {
                    "httpStatus": response.status_code,
                    "message": "Error",
                    "status": False,
                    "response": str(response.text),
                    "body": payload
                }
                capture_event(
                    {
                        'message': 'Error en subscription link1',
                        'extra': {
                            'envio': payload,
                            'response': response.text,
                        }
                    }
                )
                return None, dict_fields

    def revoke(self, token, uuid, date_cancellation):
        (sku, price_code) = self.get_campaign(self.site)

        data = {
            "sku": sku,
            "priceCode": price_code,
            "token": token,
            "expirationDateUTC": date_cancellation.strftime("%Y-%m-%dT%H:%M:%S"),
            "clientId": uuid
        }

        url = self.url + 'sales/api/v1/subscription/link/revoke'
        response = requests.put(url, headers=self.headers, json=data)
        return response

    def get_uuid_by_email(self, email):
        url = self.url + 'identity/api/v1/user'
        params = {
            'search': 'email={}'.format(email)
        }
        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            response = response.json()
            try:
                if response['result']:
                    user = response['result'][0]
                    return user['uuid']
            except Exception:
                capture_exception()
        return {}

    def connect(self, site):
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(str(settings.PAYWALL_ARC_TOKEN)),
            'Arc-Site': site
        }

        self.url = settings.PAYWALL_ARC_URL


class SalesLinked(object):
    campaign = 'collaborators'
    site = ''
    headers = {}
    url = None

    def __init__(self, site):
        self.connect(site)
        self.site = site

    def create(self, token, uuid):
        try:
            expiration_date = date.today() + relativedelta(years=100)

            (sku, price_code) = self.get_campaign(self.site)
            data = {
                "sku": sku,
                "priceCode": price_code,
                "token": str(token),
                "expirationDateUTC": expiration_date.strftime("%Y-%m-%dT%H:%M:%S") + '.000Z',
                "clientId": uuid
            }

            url = self.url + 'sales/api/v1/subscription/link'
            response = requests.post(url, headers=self.headers, json=data)
            if response.status_code != 200:
                capture_event(
                    {
                        'message': 'Error en el linkeo',
                        'extra': {
                            'respuesta': response.text,
                        }
                    }
                )
            return response, data
        except Exception:
            capture_exception()
            return None

    def revoke(self, token, uuid, date_cancellation):
        (sku, price_code) = self.get_campaign(self.site)
        # /sales/public/subscription/link/revoke
        data = {
            "sku": sku,
            "priceCode": price_code,
            "token": token,
            "expirationDateUTC": date_cancellation.strftime("%Y-%m-%dT%H:%M:%S"),
            "clientId": uuid
        }
        url = self.url + 'sales/api/v1/subscription/link/revoke'

        response = requests.put(url, headers=self.headers, json=data)
        return response

    def get_uuid_by_email(self, email):
        url = self.url + 'identity/api/v1/user'
        params = {
            'search': 'email={}'.format(email)
        }
        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            response = response.json()

            try:
                if response['result']:
                    user = response['result'][0]
                    return user['uuid']
            except Exception:
                capture_exception()

        return {}

    def get_campaign(self, site):
        sku = ''
        price_code = ''
        sales_client = SalesClient()
        self.campaign = '{}-{}'.format(self.campaign, site)
        get_campaign = sales_client.get_campaign(site, self.campaign)
        if get_campaign:
            for product in get_campaign['products']:
                if not price_code:
                    sku = product['sku']
                    sku_name = product.get('name')
                    if "colaborador" in sku_name.lower():
                        for rate in product['pricingStrategies']:
                            price_code = rate['priceCode']
                            break
                else:
                    break

        return sku, price_code

    def connect(self, site):
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(str(settings.PAYWALL_ARC_TOKEN)),
            'Arc-Site': site
        }

        self.url = settings.PAYWALL_ARC_URL


def search_user_arc_param(type, valor):
    """
        type: tipo de busqueda por email, uuid
        valor : el valor en si
    """
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % settings.PAYWALL_ARC_TOKEN,
        }

        path = "{type}={valor}".format(type=type, valor=valor)
        url = settings.PAYWALL_ARC_URL + 'identity/api/v1/user?search=' + str(path)
        response = requests.get(url, headers=headers)
        return response.json()
    except Exception as e:
        print(e)
        print('no se encontro al usuario en arc')
        return ''
