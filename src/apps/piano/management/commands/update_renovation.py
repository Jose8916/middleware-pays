# -*- coding: utf-8 -*-
import csv
import json
from django.db.models import Min, Max
from django.core.management.base import BaseCommand
from apps.piano.models import RenovationPiano
from apps.siebel.models import LogRenovationPiano
from django.utils import formats, timezone
from datetime import datetime


class Command(BaseCommand):
    help = 'Ejecuta el comando'
    #'python3 manage.py update_initial_payment

    def add_arguments(self, parser):
        parser.add_argument('--test', nargs='?', type=str)

    def handle(self, *args, **options):
        """
            - actualiza el pago inicial de la suscripcion
        """
        ############ DESCARGA ##########
        renovations = RenovationPiano.objects.filter(state=False)
        for renovation in renovations.iterator():
            respuesta = False
            log_transactions = LogRenovationPiano.objects.filter(transaction__siebel_renovation=renovation)
            for log_transaction in log_transactions:
                response_log = log_transaction.siebel_response
                try:
                    response_dict = json.loads(response_log.replace("\'", "\""))
                    respuesta_response = response_dict.get('response')
                    respuesta = int(respuesta_response.get('respuesta'))
                    if respuesta == 1:
                        respuesta = True
                    else:
                        respuesta = False
                except Exception as e:
                    respuesta = False

                if respuesta:
                    print(log_transaction.transaction.payu_transaction_id)
                    if not options['test']:
                        print('ingresa')
                        renovation.state = respuesta
                        renovation.siebel_response = log_transaction.siebel_response
                        renovation.save()
                    break
        print('Termino ejecucion de comando')
