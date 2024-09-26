# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import formats, timezone
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

    def get_start_subscription(self):
        # obtiene la fecha de inicio de las suscripciones PIANO
        try:
            tz = timezone.get_current_timezone()
            date_time_obj = datetime.strptime('05/26/2022', '%m/%d/%Y')
            return date_time_obj.astimezone(tz)
        except Exception as e:
            print(e)
            return ''

    def date_str_to_date(self, date_str):
        tz = timezone.get_current_timezone()
        date_obj = datetime.strptime(date_str, "%m/%d/%Y %H:%M")
        return date_obj.astimezone(tz)

    def handle(self, *args, **options):
        path = '/home/milei/Documentos/subscription_migration/'
        rama = options['rama']
        brand = options.get('site')

        name_file_migration_subscriptions = '/home/milei/Escritorio/totales/archivo_formateado2.csv'.format(
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
                    'subscription_id',
                    'term_id',
                    'next_billing_date',
                    'last_billing_piano',
                    'subsription_id_arc',
                    'next_billing_date_arc'
                ]
            )

            with open('/home/milei/Escritorio/totales/archivo_formateado.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if self.date_str_to_date(row.get('next_billing_date_arc')) < self.get_start_subscription():
                        writer.writerow(
                            [
                                row.get('user_id'),
                                row.get('subscription_id'),
                                row.get('term_id'),
                                row.get('next_billing_date_piano'),
                                row.get('last_billing_piano'),
                                row.get('subsription_id_arc'),
                                row.get('next_billing_date_arc')
                            ]
                        )
                    else:
                        print(row.get('subscription_id'))
            csvfile.close()
        print('Termino la ejecucion del comando')
