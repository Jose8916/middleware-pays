# -*- coding: utf-8 -*-
import csv
import json
from django.db.models import Min, Max
from django.core.management.base import BaseCommand
from apps.piano.models import RenovationPiano
from apps.siebel.models import SiebelConfirmationPayment
from django.utils import formats, timezone
from datetime import datetime
from django.db.models import Count


class Command(BaseCommand):
    help = 'Ejecuta el comando que agrega el transaction id de cada peticion'
    #'python3 manage.py update_initial_payment

    def add_arguments(self, parser):
        parser.add_argument('--confirmation', nargs='?', type=str)
        parser.add_argument('--renovation', nargs='?', type=str)

    def handle(self, *args, **options):
        if options.get('renovation', None):
            ############ DESCARGA ##########
            list_transactions = []
            list_repeated = []
            list_renovations = RenovationPiano.objects.filter(state=True)

            for renovation in list_renovations.iterator():
                if renovation.payu_transaction_id in list_transactions:
                    list_repeated.append(renovation.payu_transaction_id)
                else:
                    list_transactions.append(renovation.payu_transaction_id)
            print(list_repeated)
            return ''

        if options.get('confirmation'):
            list_transactions = []
            list_repeated = []
            list_siebel_confirmation = SiebelConfirmationPayment.objects.filter(cod_delivery__isnull=False)
            for confirmation in list_siebel_confirmation.iterator():
                if confirmation.cod_delivery and confirmation.num_liquidacion:
                    key_valid = str(confirmation.cod_delivery) + ' ' + confirmation.num_liquidacion
                    if key_valid in list_transactions:
                        list_repeated.append(
                            {
                                'num_liquidacion': key_valid,
                                'created': confirmation.created
                            }
                        )
                    else:
                        list_transactions.append(key_valid)

            print(list_repeated)
            with open('/tmp/lista_confirmacion.csv', 'a', encoding="utf-8") as csvFileWrite:
                writer = csv.writer(csvFileWrite)

                for repeated in list_repeated:
                    writer.writerow(
                        [
                            repeated.get('num_liquidacion'),
                            repeated.get('created'),
                        ]
                    )



