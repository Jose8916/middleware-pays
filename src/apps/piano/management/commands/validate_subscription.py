# -*- coding: utf-8 -*-
import csv
import time
from django.conf import settings
from django.core.management.base import BaseCommand
from apps.piano.models import Transaction, Term, Subscription
from apps.paywall.models import Subscription as SubscriptionArc
from django.utils import formats, timezone
from datetime import datetime
from apps.piano.piano_clients import VXClient


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
        print('Validando Gestion')
        subscriptions = Subscription.objects.filter(app_id=settings.PIANO_APPLICATION_ID['gestion'])
        for subscription in subscriptions.iterator():
            subscription = VXClient().get_subscription('gestion', subscription.subscription_id)
            try:
                subscription = subscription.get('subscription')
            except:
                subscription = ''
            if not subscription:
                print('no pertenece a gestion')
                print(subscription.subscription_id)

        print("Termino de validar gestion")

        print('Validando Comercio')
        subscriptions = Subscription.objects.filter(app_id=settings.PIANO_APPLICATION_ID['elcomercio'])
        for subscription in subscriptions.iterator():
            subscription = VXClient().get_subscription('elcomercio', subscription.subscription_id)
            try:
                subscription = subscription.get('subscription')
            except:
                subscription = ''
            if not subscription:
                print('no pertenece a elcomercio')
                print(subscription.subscription_id)

        print("Termino de validar gestion")


