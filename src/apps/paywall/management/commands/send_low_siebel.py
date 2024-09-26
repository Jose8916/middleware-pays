# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from sentry_sdk import capture_exception

from apps.paywall.models import Operation, Subscription
from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, SiebelConfirmationPayment
from ...utils_siebel import SiebelConciliationSender
from datetime import datetime, timedelta
from django.db.models import Count
from apps.paywall.arc_clients import SalesClient
from apps.siebel.clients.unsubscribe import UnsubscribeClient


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def add_arguments(self, parser):
        parser.add_argument('--days_ago', nargs='?', type=str)
        parser.add_argument('--filter_elements', nargs='?', type=str)
        parser.add_argument('--test_mode', nargs='?', type=str)

    def handle(self, *args, **options):
        """
            python3 manage.py send_low_siebel --days_ago 2 --test_mode 1
        """

        test_mode = True if options.get('test_mode', '') == '1' else False
        config_siebel = SiebelConfiguration.objects.get(state=True)
        if not config_siebel.blocking:
            ahora = datetime.utcnow()
            last_month = datetime.utcnow() - timedelta(days=int(config_siebel.days_ago))

            subscription_list = Subscription.objects.filter(
                state=Subscription.ARC_STATE_TERMINATED,
                date_anulled__range=[last_month, ahora]
            ).exclude(siebel_arc_unsubscribe__sent_to_siebel=True)

            for subs in subscription_list:
                op = Operation.objects.filter(payment__subscription=subs).order_by('payment__date_payment').last()
                try:
                    valid_op = int(op.conciliation_cod_response)
                except:
                    valid_op = ''
                if valid_op == 1:
                    UnsubscribeClient().siebel_suspend(subs, test_mode)
        print('Termino la ejecucion de comando')


