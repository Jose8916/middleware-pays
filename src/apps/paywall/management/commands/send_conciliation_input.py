# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from sentry_sdk import capture_exception

from apps.paywall.models import Operation, Subscription
from apps.siebel.models import SiebelConfiguration, ReasonExclude
from ...utils_siebel import SiebelConciliationSender
from datetime import datetime, timedelta
from django.db.models import Count
from apps.paywall.arc_clients import SalesClient


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def add_arguments(self, parser):
        parser.add_argument('--subscription_id', nargs='?', type=str)
        parser.add_argument('--first_sale', nargs='?', type=str)
        parser.add_argument('--recurrence', nargs='?', type=str)

    def handle(self, *args, **options):
        """
            - Servicio que envia los pagos a siebel
            - valida que en el primer servicio de siebel aya sido enviado(wsSuscripcionesPaywall/renovar.suscripcion?codDelivery)
              recurrencia_response__contains = 'Correcto',
            - valida que en el segundo servicio de siebel aya sido enviado conciliation_cod_response
            - forma de envio python3 manage.py send_conciliation --first_sale 1
            - forma de envio python3 manage.py send_conciliation --recurrence 1
        """
        list_subscriptions = ['2340797961937327', '3003826307500218', '6164383837167315', '3624720637372103',
                              '3487890431010461',
                              '7364527341090878', '1687710875315917', '1930628619552609', '6657177220475049',
                              '6937755027000617',
                              '1661446800151539', '8629051341931056', '8700636338583259', '3752732716363940',
                              '5698180553543034',
                              '6044762962143990', '6876311510976850', '4231818569267421', '1263171562434550',
                              '8611055149172798',
                              '538298809984049', '1959444103114791', '6622819652213395', '1780507881354760',
                              '1588169777338667',
                              '6468327161261155', '4021605958448155', '776938863806532']

        operation_list = Operation.objects.filter(
            conciliation_siebel_hits__lte=2,
            ope_amount__gte=5,
            payment__pa_origin='WEB',
            payment_profile__siebel_entecode__isnull=False,
            payment_profile__siebel_entedireccion__isnull=False,
            payment__subscription__arc_id__in=list_subscriptions,
        )
        print(operation_list)
        print(operation_list.query)
        operation_list = operation_list.order_by('payment__date_payment')

        for operation in operation_list:
            print(operation.payment.subscription.arc_id)
            siebel_client = SiebelConciliationSender(operation)

            try:
                siebel_client.send_conciliation()
            except Exception:
                capture_exception()
