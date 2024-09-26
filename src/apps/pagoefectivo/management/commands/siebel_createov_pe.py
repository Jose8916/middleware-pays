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

    def add_arguments(self, parser):
        parser.add_argument('--subscription_id', nargs='?', type=str)
        parser.add_argument('--load_transactions_id', nargs='?', type=str)
        parser.add_argument('--inicio', nargs='?', type=str)
        parser.add_argument('--type', nargs='?', type=str)

    def handle(self, *args, **options):
        list_reason = []

        config_siebel = SiebelConfiguration.objects.get(state=True)
        if not config_siebel.blocking:
            ahora = datetime.utcnow()
            last_month = ahora - timedelta(days=int(config_siebel.days_ago))

            reasons = ReasonExclude.objects.all()
            for reason in reasons:
                list_reason.append(str(reason.reason))

            operation_list = CIP.objects.filter(
                state=CIP.STATE_CANCELLED,
                siebel_sale_order__delivery__isnull=True,
                created__range=[last_month, ahora]
            ).exclude(payment_profile__siebel_entecode=None)\
                .exclude(payment_profile__siebel_name=None)

            for reason in list_reason:
                operation_list = operation_list.exclude(subscription__motive_anulled__contains=reason)

            for operation in operation_list:
                siebel_client = SiebelSubscriptionSender(operation)
                print(operation.id)
                try:
                    siebel_client.send_subscription()
                except Exception:
                    capture_exception()

