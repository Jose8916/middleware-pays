# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from sentry_sdk import capture_exception

from apps.paywall.models import Operation, Subscription
from ...utils_siebel import SiebelConciliationSender
from datetime import datetime
from django.db.models import Count


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def add_arguments(self, parser):
        parser.add_argument('--subscription_id', nargs='?', type=str)

    def handle(self, *args, **options):
        """
            - Servicio que envia los pagos a siebel
            - valida que en el primer servicio de siebel aya sido enviado(wsSuscripcionesPaywall/renovar.suscripcion?codDelivery)
              recurrencia_response__contains = 'Correcto',
            - valida que en el segundo servicio de siebel aya sido enviado conciliation_cod_response
        """
        list_exclude = ['640465', '640467', '640485', '640494', '640503', '640530', '640545', '640617', '640620',
                        '640640', '640648', '640713', '640725', '640786', '640814', '640892', '640898', '641011',
                        '641035']

        lista = ['48333', '48268', '48334', '48336', '48376', '48374', '48357', '48375', '46235', '46181', '48426',
                 '46205', '46274', '46223', '46384', '46276', '46288', '46234', '46333', '46383', '46335', '46352',
                 '46407', '46410', '46411', '46430', '46429', '46470', '46432', '46469', '46435', '46488', '46506',
                 '46552', '46508', '46531', '46353', '46436', '46600', '46289', '46180', '46224', '46291', '46572',
                 '46632', '46603', '46604', '46692', '46799', '46651', '46666', '46667', '46668', '46704', '46910',
                 '46775', '46934', '46935', '46979', '46797', '46848', '46991', '47040', '47005', '47145', '47059',
                 '47085', '47117', '47116', '47119', '47247', '47369', '47378', '47558', '47367', '47427', '47417',
                 '47446', '47469', '47529', '47534', '47670', '47876', '47581', '47686', '47761', '47817', '47743',
                 '47816', '47851', '47941', '47942', '47966', '47899', '47987', '48063', '47988', '47990', '48016',
                 '48050', '48061', '48062', '48064', '47965', '48033', '48091', '48092', '48131', '48154', '48085',
                 '48158', '48186', '48189', '48229', '48264']

        current_month = datetime.now().month
        operation_list = Operation.objects.filter(
            id__in=lista,
            ope_amount__gte=5
        ).filter(
            Q(conciliation_cod_response__isnull=True) | Q(conciliation_cod_response='')
            | Q(conciliation_cod_response__exact='') | Q(conciliation_cod_response='0')
            | Q(conciliation_cod_response__exact='0') | Q(conciliation_cod_response=0)
        ).order_by('payment__date_payment')

        for operation in operation_list:
            print(str(operation.id) + '-' + str(operation.siebel_delivery) + '-' + str(operation.payment.subscription.arc_id))
            siebel_client = SiebelConciliationSender(operation)
            try:
                siebel_client.send_conciliation()
            except Exception:
                capture_exception()

