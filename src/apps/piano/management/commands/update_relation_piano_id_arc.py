# -*- coding: utf-8 -*-
import csv
import time
from django.db.models import Min, Max
from django.core.management.base import BaseCommand
from apps.piano.models import Transaction, Term, Subscription, SubscriptionMatchArcPiano, TransactionsWithNewDate
from apps.paywall.models import Subscription as SubscriptionArc
from django.utils import formats, timezone
from datetime import datetime


class Command(BaseCommand):
    help = 'Ejecuta el comando'
    #'python3 manage.py update_initial_payment

    def handle(self, *args, **options):
        """
            - actualiza el pago inicial de la suscripcion
        """
        print('Inicio de comando')
        path_source = '/tmp/correccion_relaciones_ec.csv'

        with open(path_source) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                transactions = Transaction.objects.filter(
                    subscription_id_str=row.get('suscripcion_id_piano', '')
                )
                for transaction in transactions:
                    print('transaccion ' + str(transaction.subscription_id_str))
                    break
                print('Termino validacion 1')

                subscriptions = SubscriptionMatchArcPiano.objects.filter(
                    subscription_id_piano=row.get('suscripcion_id_piano', '')
                )
                for subcription in subscriptions:
                    print('actualizado ' + str(row.get('id_arc_corregido', '')))
                    subcription.subscription_id_arc = row.get('id_arc_corregido', '')
                    subcription.save()
                print('Termino validacion 2')

                transactions = TransactionsWithNewDate.objects.filter(
                    subscription_id_piano=row.get('suscripcion_id_piano', '')
                )
                for transaction in transactions:
                    print('new_date ' + str(transaction.subscription_id_piano))
                    break
        print('Termino la ejecucion del comando')





