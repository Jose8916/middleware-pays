from datetime import datetime
import time
from django.utils import formats, timezone
from django.conf import settings
from django.utils.timezone import get_default_timezone
from sentry_sdk import capture_exception, capture_event, push_scope
from suds.bindings import binding
from suds.client import Client as SudsClient
from suds.plugin import MessagePlugin
from suds.sudsobject import asdict
import requests

from apps.arcsubs.utils import timestamp_to_datetime
from apps.paywall import soap_utils
from apps.paywall.models import FinancialTransaction, Payment, Operation
from apps.siebel.models import Rate, LogSiebelClient, LogSiebelOv, LogSiebelConciliacion, PendingSendSiebel, SiebelConfirmationPayment
from django.core.management.base import BaseCommand

binding.envns = ('soapenv', 'http://schemas.xmlsoap.org/soap/envelope/')


class Command(BaseCommand):
    def valid_last_payment(self, operation):
        """
            verifica que la anterior transaccion sea cero
        """
        operations_objs = Operation.objects.filter(
            payment__subscription__arc_id=operation.payment.subscription.arc_id
        ).order_by(
            'payment__date_payment'
        )

        for operation_obj in operations_objs:
            if operation_obj.payment.arc_order == operation.payment.arc_order:
                if last_object.ope_amount == 0:
                    return True
            last_object = operation_obj

        return False

    def handle(self, *args, **options):

        xdata = {
            'tem:cod_ente': 1816686,
            'tem:cod_suscripcion': 707052
        }
        # Filtro para documentos no recepcionados de la primera venta
        Operation.objects.filter(
            payment__pa_origin='WEB',
            creation_date_delivery > today + 3,
            siebel_operation__isnull=True
        )
        # Filtro para documentos no recepcionados de la primera venta - con precio de inicio cero
        operations = Operation.objects.filter(
            payment__pa_origin='RECURRENCE',
            creation_date_delivery > today + 3,
            siebel_operation__isnull=True
        )
        for operation in operations:
            if self.valid_last_payment(operation):
                list_operation.append(operation)


        SiebelConfirmationPayment.objects.filter(
            operation=None,
            cip=None
        )
        print(xdata)
        print('---------')
        print(response)
