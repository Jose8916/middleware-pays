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

    def get_customer_reference(self, id):
        import requests
        import json
        url = "https://api.paymentsos.com/customers?customer_reference=" + id
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

        with open('/home/milei/Escritorio/payu/delta_arc.csv', 'a', encoding="utf-8") as csvFilewrite:
            writer = csv.writer(csvFilewrite)
            writer.writerow(
                [
                    'user_id',
                    'customer_id',
                    'token_hub',
                    'token_latam'
                ]
            )
            contar = 0
            with open('/home/milei/Escritorio/payu/uid.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    response_list = self.get_customer_reference(row.get('reference'))
                    if len(response_list) > 1:
                        print(row.get('reference'))

                    for response in response_list:
                        for tokens in response.get('payment_methods'):
                            writer.writerow(
                                [
                                    row.get('uuid'),
                                    response.get('id'),
                                    tokens.get('token'),
                                    tokens.get('additional_details').get('lat_token')
                                ]
                            )
            csvfile.close()
        print('Termino la ejecucion del comando')
