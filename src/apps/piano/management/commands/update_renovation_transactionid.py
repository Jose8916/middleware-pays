# -*- coding: utf-8 -*-
import csv
import json
from django.db.models import Min, Max
from django.core.management.base import BaseCommand
from apps.piano.models import RenovationPiano
from apps.siebel.models import LogRenovationPiano
from django.utils import formats, timezone
from datetime import datetime
from django.db.models import Count


class Command(BaseCommand):
    help = 'Ejecuta el comando que agrega el transaction id de cada peticion'
    #'python3 manage.py update_initial_payment

    def handle(self, *args, **options):

        renovations = RenovationPiano.objects.all()
        for renovation in renovations.iterator():
            renovation_request = renovation.siebel_request
            dict_siebel_request = json.loads(renovation_request.replace("'", "\""))
            if dict_siebel_request.get('num_liquidacion', None):
                renovation.payu_transaction_id = dict_siebel_request.get('num_liquidacion', None)
                renovation.save()
        print('Termino ejecucion de comando')
