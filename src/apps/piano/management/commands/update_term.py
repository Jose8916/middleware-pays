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
    help = 'Actualiza el term de la suscripcion'
    # python3 manage.py update_term

    def handle(self, *args, **options):
        """
            - actualiza el term de la suscripcion
        """
        ############ DESCARGA ##########
        subscriptions = Subscription.objects.filter(term__isnull=True)
        for subscription in subscriptions.iterator():
            transaction = Transaction.objects.filter(
                subscription=subscription
            ).first()
            try:
                if transaction.term:
                    subscription.term = transaction.term
                    subscription.save()
            except:
                pass

        print('Termino la ejecucion del comando')



