# -*- coding: utf-8 -*-
import csv
import time
from django.utils import formats, timezone
from datetime import datetime
from datetime import timedelta
from django.core.management.base import BaseCommand
from apps.piano.piano_clients import VXClient, PaymentOS, IDClient, Payu
from apps.piano.models import TransactionsWithNewDate
from django.conf import settings


class Command(BaseCommand):
    help = 'carga desde un csv las fechas generadas'
    # python3 manage.py download_low_report --brand gestion --time_sleep 60

    def add_arguments(self, parser):
        parser.add_argument('--clean', nargs='?', type=str)
        parser.add_argument('--time_sleep', nargs='?', type=str)
        parser.add_argument('--update', nargs='?', type=str)

    def format_string_to_date(self, date_time_str):
        date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
        tz = timezone.get_current_timezone()
        return date_time_obj.astimezone(tz)

    def format_timestamp_to_date(self, date_timestamp):
        date_time_obj = datetime.fromtimestamp(date_timestamp)
        tz = timezone.get_current_timezone()
        return date_time_obj.astimezone(tz)

    def handle(self, *args, **options):
        if options.get('clean'):
            TransactionsWithNewDate.objects.all().delete()
            print('base limpiada')
        if options.get('update'):
            with open('/tmp/fechas_de_periodos_de_acceso_generados_ec2.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        transaction = TransactionsWithNewDate.objects.get(
                            subscription_id_piano=row.get('suscripcion'),
                            external_tx_id=row.get('External Tx ID')
                        )
                    except:
                        transaction = None
                    if transaction:
                        transaction.brand = row.get('brand')
                        transaction.save()
        else:
            with open('/tmp/fechas_de_periodos_de_acceso_generados_ec_gestion.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if not TransactionsWithNewDate.objects.filter(
                            external_tx_id=row.get('External Tx ID'),
                            subscription_id_piano=row.get('suscripcion')
                    ).exists():
                        obj = TransactionsWithNewDate(
                            subscription_id_piano=row.get('suscripcion'),
                            external_tx_id=row.get('External Tx ID'),
                            access_from=row.get('period_from'),
                            access_to=row.get('period_to'),
                            brand=row.get('brand')
                        )
                        print('cargando fechas generadas ' + str(row.get('External Tx ID')))
                        obj.save()
                    else:
                        print(row.get('External Tx ID'))
            print('Termino la ejecucion de comando.')




