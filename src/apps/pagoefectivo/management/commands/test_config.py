from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from sentry_sdk import capture_exception

from apps.pagoefectivo.utils_siebel import SiebelSubscriptionSender
from apps.paywall.models import Operation, FinancialTransaction, Subscription
from apps.paywall.arc_clients import SalesClient
from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, Rate
from apps.pagoefectivo.models import CIP
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Ejecuta el comando'
    """
        python3 manage.py siebel_createov_pe
    """

    def handle(self, *args, **options):
        list_reason = []
        print(settings.EMAIL_ADMIN_PEFECTIVO)
        print(settings.DOMAIN_PAGO_EFECTIVO)