# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from sentry_sdk import capture_exception

from apps.paywall.models import Operation
from apps.siebel.models import LogSiebelConciliacion
from ...utils_siebel import SiebelConciliationSender


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def handle(self, *args, **options):
        operation_list = Operation.objects.filter(
            conciliation_siebel_hits__gte=3,
            payment__pa_origin='WEB',
            payment__partner__partner_code='gestion'
        ).filter(
            Q(conciliation_cod_response__isnull=True) | Q(conciliation_cod_response='')
            | Q(conciliation_cod_response__exact='') | Q(conciliation_cod_response='0')
            | Q(conciliation_cod_response__exact='0') | Q(conciliation_cod_response=0)
        )

        for operation in operation_list:
            try:
                log_siebel = LogSiebelConciliacion.objects.get(operation=operation, log_response__contains='Correcto',
                                                               type='web')
            except Exception:
                print('sin envio' + str(operation.id))
                log_siebel = 0

            if log_siebel:
                print(operation.id)
                try:
                    Operation.objects.filter(id=operation.id).update(conciliation_siebel_response=log_siebel.log_response,
                                                                     conciliation_cod_response=1)
                except Exception:
                    print('error ' + str(operation.id))
