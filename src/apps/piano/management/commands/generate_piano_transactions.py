
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from apps.piano.piano_clients import VXClient
from apps.piano.utils.download_report import VXProcess
from dateutil.relativedelta import relativedelta
from apps.piano.constants import TERMS_EXCLUDE, LIST_ENABLE_SEND_SIEBEL
from django.conf import settings
import csv
import time
from apps.piano.utils.utils_functions import get_start_subscription
from django.utils import formats, timezone


class Command(BaseCommand):
    help = 'genera el archivo de base para la generacion de las fechas de acceseo corregidas'
    """
        python3 manage.py generate_piano_transactions --brand 'elcomercio' --days_ago 1440 --time_sleep 100
        python3 manage.py generate_piano_transactions --brand 'gestion' --days_ago 1440 --time_sleep 100
        # 24a61f1f-6140-4f07-bf11-ac221f7b2e60 ese uuid aparece como desabilitado
    """
    def add_arguments(self, parser):
        parser.add_argument('--days_ago', nargs='?', type=str)
        parser.add_argument('--brand', nargs='?', type=str)
        parser.add_argument('--time_sleep', nargs='?', type=str)

    def get_format_date(self, date_to_split):
        list_date = date_to_split.split("/")
        if len(list_date[2]) == 2:
            return list_date[0] + '/' + list_date[1] + '/20' + list_date[2]
        return date_to_split

    def update_to_timestamp(self, date_to_update):
        # '04/19/2022 11:23'
        date_time_obj = int(datetime.strptime(date_to_update, "%m/%d/%Y").timestamp())
        return date_time_obj

    def format_date_str(self, date_time_str):
        tz = timezone.get_current_timezone()
        date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
        return date_time_obj.astimezone(tz)

    def compare_dates(self, next_billing_date, fecha_de_inicio_piano):
        if next_billing_date and fecha_de_inicio_piano:
            next_billing_date_obj = datetime.strptime(next_billing_date, "%Y-%m-%d %H:%M:%S")
            fecha_de_inicio_piano_obj = datetime.strptime(fecha_de_inicio_piano, "%Y-%m-%d %H:%M")
            if next_billing_date_obj.day != fecha_de_inicio_piano_obj.day:
                return True
            else:
                return False
        else:
            False

    def get_range_days(self, days_ago):
        date_now_ = datetime.now()
        date_from = date_now_ - timedelta(days=days_ago)

        date_from_timestamp = int(date_from.timestamp())
        date_to_timestamp = int(date_now_.timestamp())
        return date_from_timestamp, date_to_timestamp

    def handle(self, *args, **options):
        brand = options.get('brand')
        path_source = '/home/milei/Documentos/subscription_migration/production_' + brand + '/backup/update/'
        date_interval = 'MONTH'
        days_ago = options.get('days_ago')
        date_from, date_to = self.get_range_days(int(days_ago))
        print(date_from)
        print(date_to)
        time_sleep = int(options.get('time_sleep'))

        ############ DESCARGA suscripciones ##########
        report_id = VXClient().get_subscription_details_report(brand, inactive_subscriptions=False)
        export = report_id.get('export', '')
        export_id = export.get('export_id', '')
        time.sleep(time_sleep)
        export_csv_link = VXClient().get_export_download(brand, export_id)
        url = export_csv_link.get('data', '')
        list_subscriptions = VXClient().get_csv_subscription_detail_from_url(url)
        if not list_subscriptions:
            print('error en descarga de suscripciones')
        ############ DESCARGA ##########

        list_subs_match_piano_arc = []
        with open(path_source + 'match_arc_piano.csv') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                list_subs_match_piano_arc.append(
                    {
                        'sub_arc': row.get('SubscripcionId ARC', ''),
                        'sub_piano': row.get('Suscripcion Id PIANO', '')
                    }
                )
        list_next_billing_date_arc = []
        if brand == 'elcomercio':
            name_file = 'Enoqbpnkpu_subs_payu.csv'
        elif brand == 'gestion':
            name_file = 'UmAkgzZ4pu_subs_payu.csv'
        with open(path_source + name_file) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                list_next_billing_date_arc.append(
                    {
                        'sub_arc': row.get('suscription_id', ''),
                        'next_billing_date_arc': row.get('next_billing_date_original', '')
                    }
                )

        list_transactions = VXProcess().get_list_transactions_report(brand, date_from, date_to, int(time_sleep))
        if not list_transactions:
            print('error en descarga de pagos')

        list_transactions_recognition = VXProcess().get_list_recognition_transactions_report(
            brand, date_from, date_to, date_interval, int(time_sleep))
        if not list_transactions_recognition:
            print('error en descarga de recognition')

        with open(path_source + '/archivo_base.csv', 'a', encoding="utf-8") as csvFilewrite:
            writer = csv.writer(csvFilewrite)
            writer.writerow(
                [
                    'External Tx ID',
                    'Subscription ID',
                    'Term ID',
                    'Term Name',
                    'access from',
                    'access to',
                    'next_billing_date_arc',
                    'Tx Type',
                    'Status',
                    'User ID(UID)',
                    'arc_subs_id',
                    'start_date_subscription',
                    'status_scription'
                ]
            )
            for transaction_ in list_transactions:
                access_from = access_to = next_billing_date_arc = sub_arc_ = ''
                for sub_ in list_subscriptions:
                    if transaction_.get('subscription_id') == sub_.get('subs_id'):
                        start_date = sub_.get('start_date'),
                        status = sub_.get('status')
                        break

                if self.format_date_str(start_date[0]) < get_start_subscription(settings.PIANO_APPLICATION_ID[brand]) \
                        or transaction_.get('subscription_id') in LIST_ENABLE_SEND_SIEBEL:
                    for transaction_recognition in list_transactions_recognition:
                        if transaction_recognition.get('external_tx_id') == transaction_.get('external_tx_id'):
                            access_from = transaction_recognition.get('access_from')
                            access_to = transaction_recognition.get('access_to')
                            break

                    for match_arc in list_subs_match_piano_arc:
                        if transaction_.get('subscription_id') == match_arc.get('sub_piano'):
                            for next_arc in list_next_billing_date_arc:
                                if next_arc.get('sub_arc') == match_arc.get('sub_arc'):
                                    next_billing_date_arc = next_arc.get('next_billing_date_arc')
                                    break
                            break

                    writer.writerow(
                        [
                            transaction_.get('external_tx_id'),
                            transaction_.get('subscription_id'),
                            transaction_.get('term_id'),
                            transaction_.get('term_name'),
                            access_from,
                            access_to,
                            next_billing_date_arc,
                            transaction_.get('tx_type'),
                            transaction_.get('status'),
                            transaction_.get('user_id'),
                            sub_arc_,
                            start_date[0],
                            status
                        ]
                    )

        return 'completado'
