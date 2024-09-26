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
            data_order = SalesClient().get_order(
                site=brand,
                order_id=row.get('order_number')
            )

            if data_order:
                if len(data_order.get('items')) > 1:
                    print('algo raro')
                    print(data_order.get('orderNumber'))
                    print('-----------')

                if len(data_order.get('payments')) > 1:
                    print('algo raro 2')
                    print(data_order.get('orderNumber'))
                    print('***********')

                if len(data_order.get('subscriptionIDs')) > 1:
                    print('algo raro 3')
                    print(data_order.get('orderNumber'))
                    print('+++++++++++')

                for subscription in data_order.get('subscriptionIDs'):
                    subscription_obj = subscription
                    break

                for payment in data_order.get('payments'):
                    credit_card_type = payment.get('paymentMethod').get('creditCardType')
                    first_six = payment.get('paymentMethod').get('firstSix')
                    last_four = payment.get('paymentMethod').get('lastFour')
                    card_holder_name = payment.get('paymentMethod').get('cardHolderName')
                    identification_number = payment.get('paymentMethod').get('identificationNumber')
                    payment_partner = payment.get('paymentMethod').get('paymentPartner')
                    payment_method_id = payment.get('paymentMethod').get('paymentMethodID')
                    break

                for item in data_order.get('items'):
                    sku = item.get('sku'),
                    price_code = item.get('priceCode')
                    break
                writer.writerow(
                    [
                        data_order.get('email'),
                        data_order.get('orderNumber'),
                        data_order.get('orderType'),
                        data_order.get('phone'),
                        data_order.get('status'),
                        sku,
                        price_code,
                        credit_card_type,
                        first_six,
                        last_four,
                        card_holder_name,
                        identification_number,
                        payment_partner,
                        payment_method_id,
                        data_order.get('billingAddress').get('line2'),
                        data_order.get('billingAddress').get('country'),
                        subscription_obj,
                        timestamp_to_datetime(data_order.get('orderDate'))
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

        name_file_migration_subscriptions = '{path}{rama}_{brand}/backup/ordenes.csv'.format(
            brand=brand,
            path=path,
            rama=options['rama']
        )
        with open(name_file_migration_subscriptions, 'a', encoding="utf-8") as csvFilewrite:
            writer = csv.writer(csvFilewrite)
            writer.writerow(
                [
                    'email',
                    'orderNumber',
                    'orderType',
                    'phone',
                    'status',
                    'sku',
                    'price_code',
                    'credit_card_type',
                    'first_six',
                    'last_four',
                    'card_holder_name',
                    'identification_number',
                    'payment_partner',
                    'payment_method_id',
                    'line2',
                    'country',
                    'subscription_obj',
                    'orderDate'
                ]
            )

            tiempo_ini = datetime.now()
            name_suscriptions = '{path}{rama}_{brand}/backup/backup_production_with_payments.csv'.format(
                brand=brand,
                path=path,
                rama=rama
            )
            with open(name_suscriptions) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    list_subscriptions.append(
                        {
                            'order_number': row.get('orderNumber'),
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

