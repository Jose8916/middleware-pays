# -*- coding: utf-8 -*-
import csv
import time
from django.utils import formats, timezone
from datetime import datetime
from datetime import timedelta
from django.core.management.base import BaseCommand
from apps.piano.piano_clients import VXClient, PaymentOS, IDClient, Payu
from apps.piano.models import LowSubscriptions
from django.conf import settings
from apps.piano.utils_models import get_or_create_subscription


class Command(BaseCommand):
    help = 'Ejecuta el comando'
    # python3 manage.py download_low_report --brand gestion --time_sleep 60

    def add_arguments(self, parser):
        parser.add_argument('--brand', nargs='?', type=str)
        parser.add_argument('--time_sleep', nargs='?', type=str)

    def get_range_days(self):
        date_now_ = datetime.now()
        date_from = date_now_ - timedelta(days=7)
        date_from_timestamp = int(date_from.timestamp())
        date_to_timestamp = int(date_now_.timestamp())
        return date_from_timestamp, date_to_timestamp

    def format_string_to_date(self, date_time_str):
        date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
        tz = timezone.get_current_timezone()
        return date_time_obj.astimezone(tz)

    def format_timestamp_to_date(self, date_timestamp):
        date_time_obj = datetime.fromtimestamp(date_timestamp)
        tz = timezone.get_current_timezone()
        return date_time_obj.astimezone(tz)

    def handle(self, *args, **options):
        """
            - Descarga de pagos de piano
            - python3 manage.py download_low_report --brand gestion
        """
        ############ DESCARGA ##########
        brand = options.get('brand')
        time_sleep = int(options.get('time_sleep'))
        report_id = VXClient().get_subscription_details_report(brand, inactive_subscriptions=True)
        export = report_id.get('export', '')
        export_id = export.get('export_id', '')
        time.sleep(time_sleep)
        export_csv_link = VXClient().get_export_download(brand, export_id)
        url = export_csv_link.get('data', '')
        list_transactions = VXClient().get_csv_subscription_detail_from_url(url)

        ############ DESCARGA ##########

        for transaction_ in list_transactions:
            if not LowSubscriptions.objects.filter(subs_id=transaction_.get('subs_id')).exists():
                subscription = VXClient().get_subscription('gestion', transaction_.get('subs_id'))
                subscription_dict = subscription.get('subscription')
                obj = LowSubscriptions(
                    subs_id=transaction_.get('subs_id'),
                    user_email=transaction_.get('user_email'),
                    resource_name=transaction_.get('resource_name'),
                    resource_id=transaction_.get('resource_id'),
                    start_date=self.format_string_to_date(transaction_.get('start_date')),
                    status=transaction_.get('status'),
                    subscription=get_or_create_subscription(transaction_.get('subs_id'), brand),
                    low_subscription=self.format_timestamp_to_date(subscription_dict.get('end_date')),
                    user_access_expiration_date=self.format_string_to_date(transaction_.get('user_access_expiration_date'))
                )
                obj.save()
        print('Termino la ejecucion del comando')

