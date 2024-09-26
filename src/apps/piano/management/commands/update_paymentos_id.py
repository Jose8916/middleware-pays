# -*- coding: utf-8 -*-
import csv
import time
from django.db.models import Min, Max
from django.core.management.base import BaseCommand
from apps.piano.models import Transaction, Term
from django.utils import formats, timezone
from datetime import datetime
from apps.piano.utils.download_report import VXProcess


class Command(BaseCommand):
    help = 'Ejecuta el comando'
    #'python3 manage.py update_initial_payment

    def add_arguments(self, parser):
        parser.add_argument('--branch', nargs='?', type=str)
        parser.add_argument('--brand', nargs='?', type=str)

    def handle(self, *args, **options):
        """
            - actualiza el pago inicial de la suscripcion
        """
        ############ DESCARGA ##########
        transactions = Transaction.objects.filter(id_transaction_paymentos__isnull=True)
        for transaction in transactions.iterator():
            initial_transaction, reconciliation_id, id_paymentos = VXProcess().get_payment_os_data(
                {'external_tx_id': transaction.external_tx_id}
            )
            transaction.id_transaction_paymentos = id_paymentos
            transaction.save()
        print('Termino la ejecucion del comando')


