from django.core.management.base import BaseCommand
from apps.paywall.models import Operation, FinancialTransaction, Subscription, Payment, Operation
from apps.siebel.models import LoadTransactionsIdSiebel
from datetime import date, timedelta, datetime
from django.utils.encoding import smart_str
import csv
from django.utils.timezone import get_default_timezone


class Command(BaseCommand):
    help = 'comando para pruebas'
    # python manage.py report_igv --lista_payments 1

    def add_arguments(self, parser):
        parser.add_argument('--end', nargs='?', type=str)
        parser.add_argument('--start', nargs='?', type=str)
        parser.add_argument('--lista_payments', nargs='?', type=str)

    def handle(self, *args, **options):

        operation = Operation.objects.get(id=2)
        print('no {}'.format(operation.recurrencia_response_state))
        print('no {}'.format(type(operation.recurrencia_response_state)))
        '''
        operation = Operation.objects.get(id=2)
        print('nulo {}'.format(operation.recurrencia_response_state))
        print('no {}'.format(type(operation.recurrencia_response_state)))
        '''

















