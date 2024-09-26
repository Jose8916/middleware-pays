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
        subscriptions = Subscription.objects.filter(payment_profile__isnull=True)
        for subscription in subscriptions.iterator():
            transactions = Transaction.objects.filter(
                payment_profile__isnull=False,
                subscription_id_str=subscription.subscription_id
            )
            for transaction in transactions:
                if transaction.payment_profile:
                    subscription.payment_profile = transaction.payment_profile
                    subscription.save()
                    break
        print('Termino paso 1')

        subscriptions = Subscription.objects.filter(payment_profile__isnull=True)
        for subscription in subscriptions.iterator():
            try:
                subs = SubscriptionMatchArcPiano.objects.get(subscription_id_piano=subscription.subscription_id)
                subscription_id_arc = subs.subscription_id_arc
            except:
                subscription_id_arc = ''

            if subscription_id_arc:
                try:
                    subs_arc_obj = SubscriptionArc.objects.get(arc_id=subscription_id_arc)
                    profile = subs_arc_obj.payment_profile
                except:
                    profile = ''
                if profile:
                    print(subscription_id_arc)
                    subscription.payment_profile = profile
                    subscription.save()
        print("Termino la ejecucion del comando")


