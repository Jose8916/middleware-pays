# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from apps.piano.constants import TERMS_EXCLUDE
from sentry_sdk import capture_exception

from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, SiebelConfirmationPayment
from apps.piano.utils.siebel_confirmation_renovation import SiebelConciliationSender
from apps.piano.models import PaymentPiano
from apps.siebel.models import LogRenovationPiano
import csv


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def add_arguments(self, parser):
        parser.add_argument('--test_mode', nargs='?', type=str)

    def handle(self, *args, **options):
        """
            - Servicio que envia las renovaciones
            - forma de envio python3 manage.py fix_renovation_confirmation --test_mode 1
        """
        print('Inicio del comando. ')
        list_ejecutados = []
        renovation_list = PaymentPiano.objects.filter(
            state=False,
            siebel_response__contains='El número de liquidación ingresado ya existe'
        )
        for renovation in renovation_list:
            try:
                transaction_obj = Transaction.objects.get(siebel_renovation=renovation)
            except:
                print('---------------')
                print(renovation.siebel_request)
                print('---------------')
                transaction_obj = None



        with open('/tmp/lista_update' + options.get('test_mode', ''), 'a', encoding="utf-8") as csvFile:
            writer = csv.writer(csvFile)
            for item in list_ejecutados:
                writer.writerow([item])

        print('Termino la ejecucion del comando')
