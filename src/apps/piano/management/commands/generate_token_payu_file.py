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

        with open('/home/milei/Escritorio/payu/report_payu.csv', 'a', encoding="utf-8") as csvFilewrite:
            writer = csv.writer(csvFilewrite)
            writer.writerow(
                [
                    'user_id',
                    'customer_id',
                    'token'
                ]
            )
            list_payu_hub = []
            with open('/home/milei/Escritorio/payu/ElComercio_trxs_837980_781124_migracion_total.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    list_payu_hub.append({
                        'transaccion_id': row.get('transaccion_id'),
                        'customer_id': row.get('customer_id')
                    })
            list_exclude = []
            with open('/home/milei/Documentos/subscription_migration_gracia/production/backup_production_with_payments.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    reference = row.get('providerReference')
                    reference_list = reference.split("~")
                    for payu_hub in list_payu_hub:
                        if payu_hub.get('transaccion_id') == reference_list[1] and row.get('subscriptionId') not in list_exclude:
                            print(reference_list[1])
                            list_exclude.append(row.get('subscriptionId'))
                            payment_methods = self.get_customer_id(payu_hub.get('customer_id'))
                            for tokens in payment_methods.get('payment_methods'):
                                writer.writerow(
                                    [
                                        row.get('clientId'),
                                        payu_hub.get('customer_id'),
                                        tokens.get('token')
                                    ]
                                )
            csvfile.close()
        print('Termino la ejecucion del comando')
