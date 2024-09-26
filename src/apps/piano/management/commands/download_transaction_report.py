# -*- coding: utf-8 -*-
import csv
import time
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from apps.piano.models import Term, Transaction
from apps.piano.piano_clients import VXClient
from apps.piano.utils.download_report import VXProcess

from apps.siebel.models import SiebelConfiguration


class Command(BaseCommand):
    help = 'Ejecuta el comando'
    """
        - Descarga de pagos de PIANO
        - python3 manage.py download_transaction_report --brand gestion --days_ago 30
    """

    def add_arguments(self, parser):
        parser.add_argument('--brand', nargs='?', type=str)
        parser.add_argument('--time_sleep', nargs='?', type=str)
        parser.add_argument('--days_ago', nargs='?', type=str)
        parser.add_argument('--date_until', nargs='?', type=str)

    def get_range_days(self, days_ago, date_until):
        if date_until:
            date_now_ = datetime.now()
        else:
            date_now_ = datetime.strptime('07/01/2022', '%m/%d/%Y')
        date_from = date_now_ - timedelta(days=days_ago)

        date_from_timestamp = int(date_from.timestamp())
        date_to_timestamp = int(date_now_.timestamp())
        return date_from_timestamp, date_to_timestamp

    def handle(self, *args, **options):
        # Declaracion de variables
        brand = options.get('brand')
        config_siebel = SiebelConfiguration.objects.get(state=True)

        # if config_siebel.blocking:
        #    return "bloqueo de servicio"

        date_until = options.get('date_until') if options.get('date_until', '') else 0
        days_ago = options.get('days_ago') if options.get('days_ago', '') else 7
        time_sleep = options.get('time_sleep') if options.get('time_sleep') else 90
        date_interval = 'MONTH'
        date_from, date_to = self.get_range_days(int(days_ago), int(date_until))

        list_terms = VXClient().get_terms(brand)
        for term_ in list_terms.get('terms'):
            if term_.get('type') == 'payment':
                VXProcess().save_term(term_)

        # Descarga reportes de PIANO
        print(f"Date range of {date_from} To {date_to}")
        list_transactions = VXProcess().get_list_transactions_report(brand, date_from, date_to, int(time_sleep))
        list_transactions_recognition = VXProcess().get_list_recognition_transactions_report(
            brand, date_from, date_to, date_interval, int(time_sleep))

        VXProcess().report_save_transactions(list_transactions, list_transactions_recognition, brand)
        print('Termino la ejecucion del comando')

