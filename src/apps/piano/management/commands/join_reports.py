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

        name_suscriptions = '{path}{rama}_{brand}/backup/backup_production_initial_transaction.csv'.format(
            brand=brand,
            path=path,
            rama=rama
        )
        with open(name_suscriptions) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get('transaction_type') != 'created':
                    list_paymentos.append(
                        {
                            'subscriptionId': row.get('transaction_type'),
                            'initialTransaction': row.get('initialTransaction'),
                            'clientId': row.get('clientId')
                        }
                    )

        print('Termino la ejecucion del comando')

