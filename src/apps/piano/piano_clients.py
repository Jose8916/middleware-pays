import csv
import io
import time
from urllib.parse import urljoin

import requests
from django.conf import settings
from sentry_sdk import add_breadcrumb, capture_event, capture_exception


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
                return {"error": response.status_code}


class VXClient(ClientBase):

    def get_payment(self, user_payment_id, brand):

        headers = {
            'Accept': 'application/json'
        }

        url = '{domain}/{method}?aid={aid}&api_token={api_token}&user_payment_id={user_payment_id}'.format(
            domain=settings.PIANO_DOMAIN,
            method='api/v3/publisher/payment/get',
            aid=settings.PIANO_APPLICATION_ID[brand],
            api_token=settings.PIANO_API_TOKEN[brand],
            user_payment_id=user_payment_id
        )

        return self.api_request(url=url, headers=headers, json={}, method='get')

    def get_conversion(self, uid, brand):

        headers = {
            'Accept': 'application/json'
        }

        url = '{domain}/{method}?aid={aid}&api_token={api_token}&uid={uid}&limit=400&offset=0'.format(
            domain=settings.PIANO_DOMAIN,
            method='api/v3/publisher/conversion/list',
            aid=settings.PIANO_APPLICATION_ID[brand],
            api_token=settings.PIANO_API_TOKEN[brand],
            uid=uid
        )

        return self.api_request(url=url, headers=headers, json={}, method='get')

    def get_subscription(self, brand, id_subscription):

        headers = {
            'Accept': 'application/json'
        }
        url = '{domain}/{method}?aid={aid}&api_token={api_token}&subscription_id={subscription_id}'.format(
            domain=settings.PIANO_DOMAIN,
            method='api/v3/publisher/subscription/get',
            aid=settings.PIANO_APPLICATION_ID[brand],
            api_token=settings.PIANO_API_TOKEN[brand],
            subscription_id=id_subscription
        )

        return self.api_request(url=url, headers=headers, json={}, method='get')

    def registration_create(self, uid, brand, email, term_id):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        url = urljoin(
            settings.PIANO_DOMAIN,
            '/api/v3/publisher/conversion/registration/create',
        )
        PIANO_API_TOKEN = {
            'elcomercio': '1',
            'gestion': '2'
        }
        data = {
            "aid": settings.PIANO_APPLICATION_ID[brand],
            "api_token": settings.PIANO_API_TOKEN[brand],
            "email": email,
            "term_id": term_id,
            "uid": uid,
        }
        return self.api_request(url=url, headers=headers, json=data, method='post')

    def custom_create(self, uid, brand, term_id):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        url = urljoin(
            settings.PIANO_DOMAIN,
            '/api/v3/publisher/conversion/custom/create',
        )
        data = {
            "aid": settings.PIANO_APPLICATION_ID[brand],
            "api_token": settings.PIANO_API_TOKEN[brand],
            "access_period": 4000,
            "term_id": term_id,
            "uid": uid,
            "extend_existing": True,
            "unlimited_access": 1
        }
        return self.api_request(url=url, headers=headers, json=data, method='post')

    def get_terms(self, brand):

        headers = {
            'Accept': 'application/json'
        }
        url = '{domain}/{method}?aid={aid}&api_token={api_token}&limit={limit}'.format(
            domain=settings.PIANO_DOMAIN,
            method='api/v3/publisher/term/list',
            aid=settings.PIANO_APPLICATION_ID[brand],
            api_token=settings.PIANO_API_TOKEN[brand],
            limit='500'
        )

        return self.api_request(url=url, headers=headers, json={}, method='get')

    def get_term(self, brand, term_id):
        headers = {
            'Accept': 'application/json'
        }
        url = '{domain}/{method}?term_id={term_id}&api_token={api_token}'.format(
            domain=settings.PIANO_DOMAIN,
            method='api/v3/publisher/term/get',
            term_id=term_id,
            api_token=settings.PIANO_API_TOKEN[brand]
        )

        return self.api_request(url=url, headers=headers, json={}, method='get')

    def get_recognition_transactions_report(self, brand, date_from, date_to, date_interval):
        headers = {
            'Accept': 'application/json'
        }
        print("the brand is: ",brand)
        url = '{domain}/{method}?aid={app_id}&api_token={api_token}&date_interval={date_interval}&export_format=CSV&from={date_from}&to={date_to}'.format(
            domain=settings.PIANO_DOMAIN_REPORT,
            method='rest/export/schedule/revenue/recognition/transactions',
            app_id=settings.PIANO_APPLICATION_ID[brand],
            api_token=settings.PIANO_API_TOKEN[brand],
            date_interval=date_interval,
            date_from=date_from,
            date_to=date_to
        )
        return self.api_request(url=url, headers=headers, data={}, method='post')

    def get_subscription_details_report(self, brand, inactive_subscriptions):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        url = '{domain}/{method}'.format(
            domain=settings.PIANO_DOMAIN,
            method='api/v3/publisher/export/create/subscriptionDetailsReport'
        )

        payload = 'aid={app_id}&api_token={api_token}&export_name={export_name}'.format(
            app_id=settings.PIANO_APPLICATION_ID[brand],
            api_token=settings.PIANO_API_TOKEN[brand],
            export_name='subscription_details_report' + str(int(time.time()))
        )

        if inactive_subscriptions:
            payload = payload + '&search_inactive_subscriptions=1'

        return self.api_request(url=url, headers=headers, data=payload, method='post')

    def get_transactions_report(self, brand, date_from, date_to):
        headers = {
            'Accept': 'application/json'
        }
        url = '{domain}/api/v3/publisher/export/create/transactionsReport'.format(
            domain=settings.PIANO_DOMAIN
        )
        data = {
            "aid": settings.PIANO_APPLICATION_ID[brand],
            "api_token": settings.PIANO_API_TOKEN[brand],
            "date_from": date_from,
            "date_to": date_to,
            "export_name": "proceso_de_envio_a_BO",
            "order_by": "payment_date",
            "order_direction": "desc",
            "transactions_type": "all"
        }

        return self.api_request(url=url, headers=headers, data=data, method='post')

    def get_export_download(self, brand, export_id):

        headers = {
            'Accept': 'application/json'
        }

        url = '{domain}/{method}?aid={aid}&api_token={api_token}&export_id={export_id}'.format(
            domain=settings.PIANO_DOMAIN,
            method='api/v3/publisher/export/download',
            aid=settings.PIANO_APPLICATION_ID[brand],
            api_token=settings.PIANO_API_TOKEN[brand],
            export_id=export_id
        )

        return self.api_request(url=url, headers=headers, json={}, method='get')

    def get_rest_export_download(self, brand, export_id):
        headers = {
            'Accept': 'application/json'
        }
        url = '{domain}/{method}?aid={aid}&api_token={api_token}&export_id={export_id}'.format(
            domain=settings.PIANO_DOMAIN_REPORT,
            method='rest/export/download/url',
            aid=settings.PIANO_APPLICATION_ID[brand],
            api_token=settings.PIANO_API_TOKEN[brand],
            export_id=export_id
        )
        return self.api_request(url=url, headers=headers, json={}, method='get')

    def get_csv_subscription_detail_from_url(self, url):
        list_transactions = []

        try:
            r = requests.get(url)
            buff = io.StringIO(r.text)

            cr = csv.DictReader(buff)
            for row in cr:
                list_transactions.append(
                    {
                        'subs_id': row.get('ID'),
                        'user_email': row.get('User'),
                        'resource_name': row.get('Resource Name'),
                        'resource_id': row.get('Resource ID (RID)'),
                        'start_date': row.get('Start Date'),
                        'status': row.get('Status'),
                        'user_access_expiration_date': row.get('User Access Expiration Date')
                    })
            return list_transactions
        except:
            return list_transactions

    def get_csv_from_url(self, url):
        list_transactions = []

        try:
            r = requests.get(url)
            buff = io.StringIO(r.text)

            cr = csv.DictReader(buff)
            for row in cr:
                list_transactions.append(
                    {
                        'external_tx_id': row.get('External Tx ID'),
                        'user_payment_id': row.get('ID'),
                        'tx_type': row.get('Tx Type'),
                        'status': row.get('Status'),
                        'term_name': row.get('Term name'),
                        'term_id': row.get('Term ID'),
                        'subscription_id': row.get('Subscription ID'),
                        'user_id': row.get('User ID (UID)'),
                        'payment_source_type': row.get('Payment source type'),
                        'report_data': row,
                    })
            return list_transactions
        except:
            return list_transactions

    def get_csv_from_url_recognition(self, url):
        list_transactions = []

        try:
            r = requests.get(url)
            buff = io.StringIO(r.text)

            cr = csv.DictReader(buff)
            for row in cr:
                list_transactions.append(
                    {
                        'external_tx_id': row.get('External Tx Id'),
                        'access_from': row.get('Access From'),
                        'access_to': row.get('Access To'),
                        'payment_date': row.get('Payment date'),
                        'amount': row.get('Amount')
                    })
            return list_transactions
        except:
            return list_transactions


class IDClient(ClientBase):

    def get_uid(self, uid, brand):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        url = urljoin(
            settings.PIANO_DOMAIN,
            'api/v3/publisher/user/get',
        )
        data = {
            "aid": settings.PIANO_APPLICATION_ID[brand],
            "api_token": settings.PIANO_API_TOKEN[brand],
            "uid": uid,
        }

        return self.api_request(url=url, headers=headers, data=data, method='post')


class PaymentOS(ClientBase):

    def get_payment(self, app_id, private_key, id_transaction):
        if settings.ENVIRONMENT == 'production':
            x_payments_os_env = 'live'
        else:
            x_payments_os_env = 'test'

        headers = {
            'Accept': 'application/json',
            'api-version': '1.1.0',
            'x-payments-os-env': x_payments_os_env,
            'app-id': app_id,
            'private-key': private_key
        }
        url = '{domain}/{method}/{id_transaction}?expand=all'.format(
            domain='https://api.paymentsos.com',
            method='payments',
            id_transaction=id_transaction
        )

        return self.api_request(url=url, headers=headers, json={}, method='get')


class Payu(ClientBase):
     def get_transaction_by_type(self, command, type_request, value_command):
        headers = {
            'Accept': 'application/json'
        }
        data = {
            "test": False,
            "language": "en",
            "command": command,
            "merchant": {
                "apiLogin": settings.PAYU_API_LOGIN,
                "apiKey": settings.PAYU_API_KEY
            },
            "details": {
                type_request: value_command
            }
        }
        url = '{domain}/{method}'.format(
            domain=settings.PAYU_DOMAIN,
            method='reports-api/4.0/service.cgi'
        )
        return self.api_request(url=url, headers=headers, json=data, method='post')



