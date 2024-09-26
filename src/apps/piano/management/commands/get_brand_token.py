# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from sentry_sdk import capture_exception

from apps.paywall.models import Operation, Subscription
from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, SiebelConfirmationPayment, \
    SubscriptionExclude
from datetime import datetime, timedelta
from django.db.models import Count
from apps.paywall.arc_clients import SalesClient
from django.utils.encoding import smart_str
import csv
import time
from apps.piano.piano_clients import VXClient
from apps.arcsubs.utils import timestamp_to_datetime


class Command(BaseCommand):
    help = 'Ejecuta el comando'
    #  python3 manage.py update_tokens_migration --site gestion --rama production

    def add_arguments(self, parser):
        parser.add_argument('--site', nargs='?', type=str)
        parser.add_argument('--rama', nargs='?', type=str)

    def format_date_str(self, date_time_str):
        date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
        return date_time_obj.strftime("%m-%d-%Y %H:%M")

    def format_date(self, date_time):
        return date_time.strftime("%m/%d/%Y %H:%M")

    def get_customer_id(self, id):
        import requests
        import json
        url = "https://api.paymentsos.com/customers/" + str(id)
        payload = {}
        headers = {
            'Content-Type': 'application/json',
            'api-version': '1.3.0',
            'x-payments-os-env': 'live',
            'app-id': 'pe.elcomercio.paywall_renewal',
            'private-key': '6c57ee5a-fa73-4e0d-82a6-6edac90f00a5',
            'idempotency-key': 'cust-34532-trans-001356-p'
        }
        response = requests.request("GET", url, headers=headers, data=payload)
        return response.json()

    def handle(self, *args, **options):

        with open('/home/milei/Escritorio/payu/report_final_payu.csv', 'a', encoding="utf-8") as csvFilewrite:
            writer = csv.writer(csvFilewrite)
            writer.writerow(
                [
                    'user_id',
                    'customer_id',
                    'token',
                    'last_token',
                    'source',
                    'finger_print',
                    'subscription_id',
                ]
            )
            list_last_token = []
            list_token_last = []
            with open('/home/milei/Escritorio/payu/gestion-tokens.csv') as tokencsvfile:
                reader_token = csv.DictReader(tokencsvfile)
                for row_token in reader_token:
                    list_last_token.append({
                        'payu_token': row_token.get('PAYU_TOKEN'),
                        'subscription_id': row_token.get('SUBSCRIPTION_ID')
                    })
                    list_token_last.append(row_token.get('PAYU_TOKEN'))
            list_customer_id = []
            just_customer = []
            with open('/home/milei/Escritorio/payu/report_payu.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row.get('customer_id') not in just_customer:
                        just_customer.append(row.get('customer_id'))
                        list_customer_id.append({
                            'customer_id': row.get('customer_id'),
                            'user_id': row.get('user_id')
                        })

            for customer_id in list_customer_id:
                    payment_methods = self.get_customer_id(customer_id.get('customer_id'))
                    for tokens in payment_methods.get('payment_methods'):
                        if tokens.get('additional_details').get('lat_token') in list_token_last:
                            subscription_id = ''
                            for last_token in list_last_token:
                                if last_token.get('payu_token') == tokens.get('additional_details').get('lat_token'):
                                    subscription_id = last_token.get('subscription_id')
                                    break
                            writer.writerow(
                                [
                                    customer_id.get('user_id'),
                                    customer_id.get('customer_id'),
                                    tokens.get('token'),
                                    tokens.get('additional_details').get('lat_token'),
                                    tokens.get('additional_details').get('source'),
                                    tokens.get('fingerprint'),
                                    subscription_id,
                                ]
                            )
                            break
            csvfile.close()
        print('Termino la ejecucion del comando')
