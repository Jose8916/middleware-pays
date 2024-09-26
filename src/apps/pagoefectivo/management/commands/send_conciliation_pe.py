# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from sentry_sdk import capture_exception

from apps.paywall.models import Operation, Subscription
from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, SiebelConfirmationPayment
from ...utils_siebel import SiebelConciliationSender
from apps.pagoefectivo.models import CIP
from datetime import datetime, timedelta
from django.db.models import Count
from apps.paywall.arc_clients import SalesClient


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def add_arguments(self, parser):
        parser.add_argument('--subscription_id', nargs='?', type=str)
        parser.add_argument('--first_sale', nargs='?', type=str)
        parser.add_argument('--recurrence', nargs='?', type=str)
        parser.add_argument('--load_transactionid', nargs='?', type=str)
        parser.add_argument('--inicio', nargs='?', type=str)

    def handle(self, *args, **options):
        """
            - Servicio que envia los pagos a siebel
            - forma de envio python3 manage.py send_conciliation_pe
        """

        config_siebel = SiebelConfiguration.objects.get(state=True)
        if not config_siebel.blocking:
            ahora = datetime.utcnow()
            last_month = ahora - timedelta(days=int(config_siebel.days_ago))
            operation_list = []
            list_reason = []
            reasons = ReasonExclude.objects.all()
            for reason in reasons:
                list_reason.append(reason.reason)

            operation_list = CIP.objects.filter(
                siebel_sale_order__siebel_hits__lte=int(config_siebel.conciliation_attempts),
                payment_profile__siebel_entecode__isnull=False,
                payment_profile__siebel_entedireccion__isnull=False,
                siebel_sale_order__delivery__isnull=False,
                created__range=[last_month, ahora]
            ).exclude(siebel_payment__siebel_response__contains='ya se encuentra registrado')\
                .exclude(siebel_payment__cod_response=1)
            print(operation_list)
            for reason in list_reason:
                operation_list = operation_list.exclude(subscription__motive_anulled__contains=reason)

            operation_list = operation_list.order_by('payment_notification_cip__payment_date')

            for operation in operation_list:
                siebel_client = SiebelConciliationSender(operation)

                try:
                    if SiebelConfirmationPayment.objects.filter(
                            cod_delivery=operation.siebel_sale_order.delivery
                    ).exists():
                        print(operation.cip)
                        siebel_client.send_conciliation()
                except Exception:
                    capture_exception()
