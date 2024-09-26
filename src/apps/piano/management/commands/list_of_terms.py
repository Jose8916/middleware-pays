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
from apps.piano.piano_clients import VXClient


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def add_arguments(self, parser):
        parser.add_argument('--all_fields', nargs='?', type=str)
        parser.add_argument('--type_term', nargs='?', type=str)
        parser.add_argument('--branch', nargs='?', type=str)
        parser.add_argument('--brand', nargs='?', type=str)

    def handle(self, *args, **options):
        """
            - Servicio que envia los pagos a siebel
            - python3 manage.py list_of_terms --type_term payment --branch sandbox --brand gestion
        """
        path = '/home/milei/Documentos/subscription_migration/'
        branch = options.get('branch')
        brand = options.get('brand')

        if options.get('all_fields'):
            list_terms = VXClient().get_terms('elcomercio')

            with open('/home/milei/Escritorio/lista_terms.csv', 'a') as csvFile:
                writer = csv.writer(csvFile)
                count = 0
                """
                for emp in list_terms.get('terms'):
                    writer.writerow([emp.get('aid')])
                """
                for emp in list_terms.get('terms'):
                    if count == 0:
                        header = emp.keys()
                        count_keys = len(emp.keys())
                        count += 1
                    else:
                        if len(emp.keys()) > count_keys:
                            header = emp.keys()
                            count_keys = len(emp.keys())

                writer.writerow(header)
                for emp in list_terms.get('terms'):
                    list_values = []
                    for head in header:
                        try:
                            list_values.append(emp[head])
                        except:
                            pass
                    writer.writerow(list_values)

            csvFile.close()
            print('Termino la ejecucion del comando')
        else:
                list_terms = VXClient().get_terms(brand)

                with open(path + branch + '/list_terms_' + brand + '.csv', 'a') as csvFile:
                    writer = csv.writer(csvFile)
                    writer.writerow(
                        [
                            'aid',
                            'term_id',
                            'name',
                            'description',
                            'type',
                            'type_name'
                        ]
                    )
                    for emp in list_terms.get('terms'):
                        if options.get('type_term') == emp.get('type'):
                            writer.writerow(
                                [
                                    emp.get('aid'),
                                    emp.get('term_id'),
                                    emp.get('name'),
                                    emp.get('description'),
                                    emp.get('type'),
                                    emp.get('type_name')
                                ]
                            )

                csvFile.close()
                print('Termino la ejecucion del comando')

