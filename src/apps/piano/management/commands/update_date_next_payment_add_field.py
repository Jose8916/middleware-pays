# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from dateutil.relativedelta import relativedelta
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
        date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
        return date_time_obj.strftime("%m-%d-%Y %H:%M")

    def format_date(self, date_time):
        return date_time.strftime("%m/%d/%Y %H:%M")

    def update_next_billing_date(self, date_to_update):
        # '04/19/2022 11:23'
        date_time_obj = datetime.strptime(date_to_update, "%m/%d/%Y %H:%M").timestamp()
        return date_time_obj

    def handle(self, *args, **options):
        path = '/home/milei/Documentos/subscription_migration/'

        name_file_migration_subscriptions = '/home/milei/Escritorio/reporte_erick/archivo_formateado.csv'.format(
            path=path
        )

        with open(name_file_migration_subscriptions, 'a', encoding="utf-8") as csvFilewrite:
            writer = csv.writer(csvFilewrite)
            writer.writerow(
                [
                    'user_id',
                    'subscription_id',
                    'term_id',
                    'next_billing_date_piano',
                    'last_billing_piano',
                    'subsription_id_arc',
                    'next_billing_date_arc',
                    'next_billing_date_timestamp'
                ]
            )

            with open('/home/milei/Escritorio/reporte_erick/primer_formato1.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row.get('next_billing_date'):
                        next_billing_date = self.update_next_billing_date(
                            row.get('next_billing_date')
                        )
                        if next_billing_date:
                            writer.writerow(
                                [
                                    row.get('user_id'),
                                    row.get('subscription_id'),
                                    row.get('term_id'),
                                    row.get('next_billing_date'),
                                    row.get('last_billing_piano'),
                                    row.get('subsription_id_arc'),
                                    row.get('next_billing_date_arc'),
                                    next_billing_date
                                ]
                            )
                        else:
                            print(row.get('subscription_id'))
            csvfile.close()
        print('Termino la ejecucion del comando')
