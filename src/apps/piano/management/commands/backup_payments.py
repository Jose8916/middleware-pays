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
import threading
import time
from apps.piano.piano_clients import VXClient
from apps.arcsubs.utils import timestamp_to_datetime


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def add_arguments(self, parser):
        parser.add_argument('--site', nargs='?', type=str)
        parser.add_argument('--rama', nargs='?', type=str)

    def format_date_str(self, date_time_str):
        date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
        return date_time_obj.strftime("%m-%d-%Y %H:%M")

    def format_date(self, date_time):
        return date_time.strftime("%m/%d/%Y %H:%M")

    def write_migration(self, list_subs, brand, writer, flag):
        for row in list_subs:
            token = ''

            data_subscription = SalesClient().get_subscription(
                site=brand,
                subscription_id=row.get('subscriptionId')
            )
            if data_subscription:
                if row.get('initialTransaction') == 'True':
                    final_payment = data_subscription.get('paymentHistory')[-1]
                    for event in data_subscription.get('events'):
                        if event['eventType'] == "START_SUBSCRIPTION":
                            date_start_subscription = timestamp_to_datetime(event['eventDateUTC'])
                            break

                    period_to = timestamp_to_datetime(final_payment['periodTo'])
                    period_from = timestamp_to_datetime(final_payment['periodFrom'])
                    next_event_date_utc = timestamp_to_datetime(data_subscription.get('nextEventDateUTC'))
                    data_subscription.get('status')

                    writer.writerow(
                        [
                            row.get('clientId'),
                            row.get('subscriptionId'),
                            data_subscription.get('priceCode'),
                            row.get('sku'),
                            data_subscription.get('status'),
                            self.format_date(date_start_subscription) if date_start_subscription else '',
                            self.format_date(period_to) if period_to else '',
                            self.format_date(period_from) if period_from else '',
                            self.format_date(next_event_date_utc) if next_event_date_utc else '',
                            data_subscription.get('currentPaymentMethod').get('firstSix'),
                            data_subscription.get('currentPaymentMethod').get('lastFour'),
                            data_subscription.get('currentPaymentMethod').get('creditCardType'),
                            data_subscription.get('currentPaymentMethod').get('cardHolderName'),
                            data_subscription.get('currentPaymentMethod').get('paymentPartner'),
                            data_subscription.get('currentPaymentMethod').get('paymentMethodID'),
                            row.get('line2')
                        ]
                    )
            else:
                print('error_' + str(row.get('subscriptionId')))

    def handle(self, *args, **options):
        """
            - Genera el csv AID_psc_subs.csv para la migracion de terminos de pago
            - python3 manage.py backup_payments --site gestion --rama production
        """

        path = '/home/milei/Documentos/subscription_migration/'
        list_tokens = []
        list_terms = []
        list_subscriptions = []
        rama = options['rama']
        brand = options['site']

        name_file_migration_subscriptions = '{path}{rama}_{brand}/backup/suscripciones_with_card_arc2.csv'.format(
            brand=brand,
            path=path,
            rama=options['rama']
        )
        with open(name_file_migration_subscriptions, 'a', encoding="utf-8") as csvFilewrite:
            writer = csv.writer(csvFilewrite)
            writer.writerow(
                [
                    'uuid',
                    'suscriptionid_arc',
                    'price_code',
                    'sku',
                    'status',
                    'start_date',
                    'ultimo pago',
                    'proximo pago',
                    'proximo pago',
                    'firstSix',
                    'lastFour',
                    'creditCardType',
                    'cardHolderName',
                    'paymentPartner',
                    'paymentMethodID',
                    'line2'
                ]
            )

            tiempo_ini = datetime.now()
            name_suscriptions = '{path}{rama}_{brand}/backup/backup_production_initial_transaction.csv'.format(
                brand=brand,
                path=path,
                rama=rama
            )
            with open(name_suscriptions) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    list_subscriptions.append(
                        {
                            'subscriptionId': row.get('subscriptionId'),
                            'initialTransaction': row.get('initialTransaction'),
                            'clientId': row.get('clientId')
                        }
                    )

                n = 2000
                name_hilo = 0
                flag = 1
                list_of_list = [list_subscriptions[i:i + n] for i in range(0, len(list_subscriptions), n)]
                for list_subs in list_of_list:
                    name_hilo = name_hilo + 1
                    vars()['thread_' + str(name_hilo)] = threading.Thread(
                        name="hilo_" + str(name_hilo),
                        target=self.write_migration, args=(list_subs, brand, writer, flag,)
                    )
                    #time.sleep(2)
                    vars()['thread_' + str(name_hilo)].start()
                    vars()['thread_' + str(name_hilo)].join()
                    # self.write_migration(list_subs, list_terms, list_tokens, list_no_cumple_condicion, brand, writer_no_cumple_condicion, writer)
                tiempo_fin = datetime.now()
                print("tiempo transcurrido " + str(tiempo_fin - tiempo_ini))

            print('Termino la ejecucion del comando')

