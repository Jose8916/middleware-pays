# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from sentry_sdk import capture_exception

from apps.paywall.models import Operation
from ...utils_siebel import SiebelConciliationSender


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def add_arguments(self, parser):
        parser.add_argument('--op', nargs='?', type=str)

    def handle(self, *args, **options):
        if options.get('op'):
            operation_list = Operation.objects.filter(
                id=options.get('op'),
                conciliation_siebel_hits__lte=12,
                payment__pa_origin='RECURRENCE',
                ope_amount__gte=5,
                conciliation_siebel_response__contains='ya se encuentra registrado',
            )
        else:
            operation_list = Operation.objects.filter(
                conciliation_siebel_hits__lte=12,
                payment__pa_origin='RECURRENCE',
                ope_amount__gte=5,
                conciliation_siebel_response__contains='ya se encuentra registrado',
            )

        for operation in operation_list:
            print(operation.id)

            siebel_client = SiebelConciliationSender(operation)

            try:
                siebel_client.send_conciliation_recurrence()
            except Exception:
                capture_exception()

