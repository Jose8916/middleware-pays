# -*- coding: utf-8 -*-
import csv
import time
from django.db.models import Min, Max
from django.core.management.base import BaseCommand
from apps.piano.models import Transaction, Term, Subscription, SubscriptionMatchArcPiano
from apps.piano.utils.utils_functions import get_start_subscription
from apps.paywall.models import Subscription as SubscriptionArc
from apps.paywall.models import Operation as OperationArc
from django.utils import formats, timezone
from apps.piano.utils_models import get_or_create_subscription, get_payment_profile
from datetime import datetime
from django.conf import settings


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    # 'python3 manage.py update_initial_payment

    def add_arguments(self, parser):
        parser.add_argument('--log', nargs='?', type=str)

    def valid_last_payment_arc(self, piano_subs_id):
        """
            verifica que la anterior un pago anterior
        """
        if SubscriptionMatchArcPiano.objects.filter(subscription_id_piano=piano_subs_id).exists():
            try:
                obj_subs = SubscriptionMatchArcPiano.objects.get(subscription_id_piano=piano_subs_id)
            except Exception as e:
                return False
            operations_objs = OperationArc.objects.filter(
                payment__subscription__arc_id=obj_subs.subscription_id_arc
            ).order_by(
                'payment__date_payment'
            ).last()

            if operations_objs.ope_amount == 0:
                return True
            else:
                return False
        else:
            return False

    def handle(self, *args, **options):
        """
            - actualiza el pago inicial de la suscripcion
        """
        subscriptions = Subscription.objects.filter(delivery__isnull=True)
        for subscription in subscriptions:
            if self.valid_last_payment_arc(subscription.subscription_id):
                first_payment = Transaction.objects.filter(
                    subscription__subscription_id=subscription.subscription_id
                ).order_by('access_from_date').first()
                if not first_payment.initial_payment:
                    log = options.get('log', '')
                    if log:
                        print(first_payment.external_tx_id)
                    else:
                        first_payment.initial_payment = True
                        first_payment.save()

        print('Termino la ejecucion del comando')

