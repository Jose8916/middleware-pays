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

    def handle(self, *args, **options):
        path = '/home/milei/Documentos/subscription_migration/'
        rama = options['rama']
        brand = options.get('site')
        list_tokens = []
        list_terms = []

        name_file_migration_subscriptions = '{path}{rama}/{brand}_subs_payu_with_tokens.csv'.format(
            brand=settings.PIANO_APPLICATION_ID[brand],
            path=path,
            rama=rama
        )
        try:
            with open(path + rama + '/list_terms_gestion.csv') as csvfileTerms:
                reader = csv.DictReader(csvfileTerms)
                for row in reader:
                    list_terms.append({
                        'subscription_id': row.get('subscription_id', ''),
                        'term_id': row.get('term_id', '')
                    })
            csvfileTerms.close()
        except Exception as e:
            print(e)
            list_terms = []

        """
        try:
            with open('{path}{rama}/gestion_tokens_final.csv'.format(path=path, rama=rama)) as csvfileTokens:
                reader = csv.DictReader(csvfileTokens)
                for row in reader:
                    list_tokens.append({
                        'subscription_id': row.get('SUBSCRIPTION_ID', ''),
                        'payu_token': row.get('PAYU_TOKEN', ''),
                        'last_updated_utc': row.get('LAST_UPDATED_UTC', '')
                    })
            csvfileTokens.close()
        except:
            list_tokens = []
        """

        with open(name_file_migration_subscriptions, 'a', encoding="utf-8") as csvFilewrite:
            writer = csv.writer(csvFilewrite)
            writer.writerow(
                [
                    'user_id',
                    'term_id',
                    'customer_id',
                    'start_date',
                    'next_billing_date',
                    'prev_billing_date',
                    'payment_method_token',
                    'card_id',
                    'custom_billing_plan',
                    'auto_renew',
                    'provider_input_params',
                    'expiration',
                    'suscription_id',
                    'price_code',
                    'sku'
                ]
            )

            with open(path + rama + '/UmAkgzZ4pu_subs_payu.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    term_id = row.get('term_id')
                    if list_tokens:
                        token = ''
                        for token_obj in list_tokens:
                            if token_obj.get('subscription_id') == row.get('suscription_id'):
                                token = token_obj.get('payu_token')
                                break
                            else:
                                token = ''

                    for term_obj in list_terms:
                        if row.get('suscription_id') == term_obj.get('subscription_id', ''):
                            term_id = term_obj.get('term_id', '')
                            print(row.get('suscription_id'))
                            break
                    writer.writerow(
                        [
                            row.get('user_id'),
                            term_id,
                            row.get('customer_id'),
                            row.get('start_date'),
                            row.get('next_billing_date'),
                            row.get('prev_billing_date'),
                            row.get('payment_method_token'),
                            row.get('card_id'),
                            row.get('custom_billing_plan'),
                            row.get('auto_renew'),
                            row.get('provider_input_params'),
                            row.get('expiration'),
                            row.get('suscription_id'),
                            row.get('price_code'),
                            row.get('sku')
                        ]
                    )
            csvfile.close()
        print('Termino la ejecucion del comando')
