# -*- coding: utf-8 -*-
import csv
import time
from django.db.models import Min, Max
from django.core.management.base import BaseCommand
from apps.piano.models import Transaction, Term, Subscription, SubscriptionMatchArcPiano
from apps.paywall.models import Subscription as SubscriptionArc
from django.utils import formats, timezone
from datetime import datetime


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
        subscriptions = Subscription.objects.filter(uid__isnull=True)
        for subscription in subscriptions.iterator():
            transaction = Transaction.objects.filter(
                subscription_id_str=subscription.subscription_id
            ).first()
            if transaction:
                subscription.uid = transaction.user_id
                subscription.save()
        print('Termino la ejecucion del comando')
