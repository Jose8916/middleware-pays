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
    #  python3 manage.py update_date_next_payment --site gestion --rama production

    def add_arguments(self, parser):
        parser.add_argument('--site', nargs='?', type=str)
        parser.add_argument('--rama', nargs='?', type=str)

    def format_date_str(self, date_time_str):
        date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
        return date_time_obj.strftime("%m-%d-%Y %H:%M")

    def format_date(self, date_time):
        return date_time.strftime("%m/%d/%Y %H:%M")

    def update_next_billing_date(self, date_to_update):
        # '04/19/2022 11:23'
        date_time_obj = datetime.strptime(date_to_update, "%m/%d/%Y %H:%M")
        if date_time_obj.day == 20 and date_time_obj.month == 6 and date_time_obj.year == 2022:
            date_time_obj = date_time_obj + timedelta(days=8)
            return date_time_obj.strftime("%m/%d/%Y %H:%M")
        elif date_time_obj.day == 21 and date_time_obj.month == 6 and date_time_obj.year == 2022:
            date_time_obj = date_time_obj + timedelta(days=7)
        elif date_time_obj.day == 22 and date_time_obj.month == 6 and date_time_obj.year == 2022:
            date_time_obj = date_time_obj + timedelta(days=6)
            return date_time_obj.strftime("%m/%d/%Y %H:%M")
        elif date_time_obj.day == 23 and date_time_obj.month == 6 and date_time_obj.year == 2022:
            date_time_obj = date_time_obj + timedelta(days=5)
            return date_time_obj.strftime("%m/%d/%Y %H:%M")
        elif date_time_obj.day == 24 and date_time_obj.month == 6 and date_time_obj.year == 2022:
            date_time_obj = date_time_obj + timedelta(days=4)
            return date_time_obj.strftime("%m/%d/%Y %H:%M")
        elif date_time_obj.day == 25 and date_time_obj.month == 6 and date_time_obj.year == 2022:
            date_time_obj = date_time_obj + timedelta(days=3)
            return date_time_obj.strftime("%m/%d/%Y %H:%M")
        elif date_time_obj.day == 26 and date_time_obj.month == 6 and date_time_obj.year == 2022:
            date_time_obj = date_time_obj + timedelta(days=2)
            return date_time_obj.strftime("%m/%d/%Y %H:%M")
        elif date_time_obj.day == 27 and date_time_obj.month == 6 and date_time_obj.year == 2022:
            date_time_obj = date_time_obj + timedelta(days=1)
            return date_time_obj.strftime("%m/%d/%Y %H:%M")
        else:
            return date_to_update

    def handle(self, *args, **options):
        path = '/home/milei/Documentos/subscription_migration/'
        rama = options['rama']
        brand = options.get('site')

        name_file_migration_subscriptions = '/home/milei/Documentos/subscription_migration/production/4ta carga/4tacarga.csv'.format(
            brand_id=settings.PIANO_APPLICATION_ID[brand],
            path=path,
            rama=rama,
            brand=brand
        )

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

            with open('/home/milei/Documentos/subscription_migration/production/4ta carga/Enoqbpnkpu_subs_payu.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row.get('next_billing_date'):
                        next_billing_date = self.update_next_billing_date(row.get('next_billing_date'))

                    writer.writerow(
                        [
                            row.get('user_id'),
                            row.get('term_id'),
                            row.get('customer_id'),
                            row.get('start_date'),
                            next_billing_date,
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
