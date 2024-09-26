# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from apps.piano.constants import TERMS_EXCLUDE
from sentry_sdk import capture_exception

from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, SiebelConfirmationPayment
from apps.piano.utils.siebel_confirmation_renovation import SiebelConciliationSender
from apps.piano.models import Transaction, RenovationPiano, SubscriptionMatchArcPiano
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
        transactions = Transaction.objects.filter(
            siebel_payment__cod_response=True,
        ).exclude(
            siebel_renovation__state=True
        )

        with open('/tmp/list_transaction.csv', 'a', encoding="utf-8") as csvFile:
            writer = csv.writer(csvFile)
            for transaction in transactions:
                if SubscriptionMatchArcPiano.objects.filter(
                    subscription_id_piano=transaction.subscription_id_str
                ).exists():
                    try:
                        transaction_state = transaction.siebel_renovation.state
                    except:
                        transaction_state = None
                    try:
                        transaction_cod_response = transaction.siebel_payment.cod_response
                    except:
                        transaction_cod_response = None

                    writer.writerow([
                        transaction.subscription_id_str,
                        transaction_cod_response,
                        transaction_state,
                        transaction.payu_transaction_id
                    ])

        print('Termino la ejecucion del comando')
