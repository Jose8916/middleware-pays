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
        with open('/home/milei/Escritorio/reporte_erick/match_piano_arc.csv', 'a', encoding="utf-8") as csvFilewrite:
            writer = csv.writer(csvFilewrite)
            writer.writerow(
                [
                    'user_id',
                    'term_id',
                    'arc_subscription_id',
                    'piano_subscription_id'
                ]
            )
            list_piano = []
            with open('/home/milei/Escritorio/reporte_erick/piano2.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    list_piano.append({
                        'uuid': row.get('uuid'),
                        'term_id': row.get('term_id'),
                        'subscription_id': row.get('subscription_id', '')
                    })

            with open('/home/milei/Escritorio/reporte_erick/arc2.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    piano_sub = ''
                    for piano in list_piano:
                        if piano.get('uuid') == row.get('user_id') and piano.get('term_id') == row.get('term_id'):
                            piano_sub = piano.get('subscription_id')

                    writer.writerow(
                        [
                            row.get('user_id'),
                            row.get('term_id'),
                            row.get('suscription_id'),
                            piano_sub
                        ]
                    )
            csvfile.close()
        print('Termino la ejecucion del comando')
