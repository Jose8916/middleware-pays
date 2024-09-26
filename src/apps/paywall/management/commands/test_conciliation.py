from datetime import datetime
import socket
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
    def handle(self, *args, **options):
        """
        xdata = {
            'tem:cod_ente': 1733264,
            'tem:cod_suscripcion': 616401,  # id_delivery, siebel_delivery
            'tem:monto_cobrado': 100.00,  # self.operation.ope_amount,
            'tem:num_operacion': 1401611111,  # self.operation.payment.payu_order,  # payu_orderid
            'tem:fch_hra_cobro': '2022-01-13 00:35:39',
            'tem:num_liquida_id': 'ii3381bf-5f56-41ff-93fi-45i2fei12i7i',
            'tem:medio_de_pago': 'VISA',
            'tem:cod_pasarelaPago': 1,
            'tem:nro_renovacion': '8336435',
            'tem:folio': '03-0B022-2039496',
            'tem:cod_interno': 28166488
        }
        """
        xdata = {
            'tem:cod_ente': 1817016,
            'tem:cod_suscripcion': 707189,  # id_delivery, siebel_delivery
            'tem:monto_cobrado': 5.00,  # self.operation.ope_amount,
            'tem:num_operacion': 1405551854,  # self.operation.payment.payu_order,  # payu_orderid
            'tem:fch_hra_cobro': '2022-04-16 00:35:39',
            'tem:num_liquida_id': '5808200c-75f8-4129-a3b4-0e359c7f06d2',
            'tem:medio_de_pago': 'VISA',
            'tem:cod_pasarelaPago': 1,
            'tem:nro_renovacion': '10992227',
            'tem:folio': '03-0B022-5902000',
            'tem:cod_interno': 34422583
        }
        xml = soap_utils.soap.prepareConciliacion({'xdata': xdata})
        response = soap_utils.soap.sendConciliacion(xml)
        print(xdata)
        print('---------')
        print(response)
