# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from apps.paywall.models import Payment
from django.db.models import Count


class Command(BaseCommand):
    help = 'Relaciona las suscripciones y pagos a la tabla FinancialTransaction'
    # python3 manage.py update_financial_transactions --subscriptions 1

    def handle(self, *args, **options):
        transactions = Payment.objects.values('arc_order').annotate(order_count=Count('arc_order'))\
            .filter(order_count__gt=1)
        print(transactions)
        """
        lista = []
        for transaction in transactions:
            lista.append(transaction['arc_order'])
            # Payment.objects.filter(arc_order=transaction['arc_order']).delete()
            # print(str(transaction['arc_order']) + ', cantidad: ' + str(transaction['order_count']))
        """
