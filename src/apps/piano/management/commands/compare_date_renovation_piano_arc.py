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
        date_time_str = date_time_str.split(' ')
        date_time_obj = datetime.strptime(date_time_str[0], '%Y-%m-%d')
        return date_time_obj

    def format_date(self, date_time_str):
        date_time_str = date_time_str.split(' ')
        return datetime.strptime(date_time_str[0], "%m/%d/%Y")

    def update_next_billing_date(self, date_str_arc, date_str_piano):
        # '04/19/2022 11:23'
        date_time_obj = datetime.strptime(date_str_piano, "%m/%d/%Y %H:%M")
        if date_time_obj.month == 5 and date_time_obj.year == 2022:
            if 11 <= date_time_obj.day <= 17:
                return date_to_update

    def handle(self, *args, **options):
        path = '/home/milei/Documentos/subscription_migration/'
        rama = ''
        brand = ''

        name_file_migration_subscriptions = '/home/milei/Escritorio/totales/archivo_formateado_final.csv'.format(
            brand_id='',
            path=path,
            rama=rama,
            brand=brand
        )

        with open(name_file_migration_subscriptions, 'a', encoding="utf-8") as csvFilewrite:
            writer = csv.writer(csvFilewrite)
            writer.writerow(
                [
                    'user_id',
                    'subscription_id',
                    'term_id',
                    'next_billing_date_calculado',
                    'last_billing_piano',
                    'subsription_id_arc',
                    'next_billing_date_arc',
                    'next_billing_date_piano_original'
                ]
            )

            with open('/home/milei/Escritorio/totales/archivo_formateado_filtrado.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    last_billing_date_piano = self.format_date_str(row.get("last_billing_piano"))
                    next_billing_date_arc = self.format_date(row.get('next_billing_date_arc'))
                    if next_billing_date_arc and last_billing_date_piano:
                        if last_billing_date_piano != next_billing_date_arc:
                            writer.writerow(
                                [
                                    row.get('user_id'),
                                    row.get('subscription_id'),
                                    row.get('term_id'),
                                    row.get('next_billing_date_calculado'),
                                    row.get('last_billing_piano'),
                                    row.get('subsription_id_arc'),
                                    row.get('next_billing_date_arc'),
                                    row.get('next_billing_date_piano_original')
                                ]
                            )
                        else:
                            print(row.get('subscription_id'))
            csvfile.close()
        print('Termino la ejecucion del comando')
