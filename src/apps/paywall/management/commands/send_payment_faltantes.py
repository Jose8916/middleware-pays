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


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def valid_last_payment(self, operation):
        """
            verifica que la anterior un pago anterior
        """
        operations_objs = Operation.objects.filter(
            payment__subscription__arc_id=operation.payment.subscription.arc_id
        ).order_by(
            'payment__date_payment'
        )

        for operation_obj in operations_objs:
            if operation_obj.payment.arc_order == operation.payment.arc_order:
                if last_object.conciliation_cod_response == "1":
                    return True
                else:
                    return False
            last_object = operation_obj

        return False

    def add_arguments(self, parser):
        parser.add_argument('--opcion', nargs='?', type=str)

    def handle(self, *args, **options):
        """
            - envia los pagos regularizados de faltantes
            - forma de envio python3 manage.py send_payment_faltantes --opcion texto
        """

        config_siebel = SiebelConfiguration.objects.get(state=True)
        if not config_siebel.blocking:
            list_reason = []
            reasons = ReasonExclude.objects.all()
            for reason in reasons:
                list_reason.append(reason.reason)

            transaction = LoadTransactionsIdSiebel.objects.get(tipo=options.get('opcion'))
            transactions = transaction.transaction_id
            list_transactions = transactions.splitlines()

            for id_transaction in list_transactions:
                print(id_transaction)
                operation_list = Operation.objects.filter(
                    conciliation_siebel_hits__lte = int(config_siebel.conciliation_attempts),
                    ope_amount__gte=5,
                    payment__pa_origin='RECURRENCE',
                    payment_profile__siebel_entecode__isnull=False,
                    payment_profile__siebel_entedireccion__isnull=False,
                    payment__subscription__delivery__isnull=False,
                    payment__payu_transaction=id_transaction
                )

                operation_list.exclude(recurrencia_response_state=True)
                operation_list = operation_list.order_by('payment__date_payment')

                for operation in operation_list:
                    if not SalesClient().has_a_refund(operation.payment.partner.partner_code, operation.payment.arc_order):
                        siebel_client = SiebelConciliationSender(operation)
                        try:
                            print('Iniciando envio: {operation_id}'.format(operation_id=operation.id))
                            siebel_client.send_payment_faltantes()
                        except Exception:
                            capture_exception()

                        print('Termino la ejecucion del comando')
