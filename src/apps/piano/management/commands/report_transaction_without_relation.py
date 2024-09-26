# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from apps.piano.constants import TERMS_EXCLUDE
from sentry_sdk import capture_exception

from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, SiebelConfirmationPayment
from apps.piano.utils.siebel_confirmation_renovation import SiebelConciliationSender
from apps.piano.models import Transaction, Subscription, SubscriptionMatchArcPiano
from apps.siebel.models import LogRenovationPiano
from apps.piano.utils.utils_functions import (get_start_subscription)
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
        with open('/tmp/report_subscriptions_without_relacion.csv', 'a') as csvFile:
            writer = csv.writer(csvFile)
            subscriptions = Subscription.objects.all()
            for subscription in subscriptions.iterator():
                if subscription.start_date < get_start_subscription(subscription.app_id):
                    if not SubscriptionMatchArcPiano.objects.filter(
                        subscription_id_piano=subscription.subscription_id
                    ).exists():
                        writer.writerow([
                            subscription.subscription_id
                        ])

        print('Termino la ejecucion del comando')
