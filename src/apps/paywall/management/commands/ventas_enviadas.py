from django.core.management.base import BaseCommand
from apps.paywall.models import Operation, FinancialTransaction, Subscription
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def handle(self, *args, **options):
        ahora = datetime.utcnow()
        end_month = ahora - timedelta(days=27)
        start_month = ahora - timedelta(days=60)
        operations = Operation.objects.filter(
            conciliation_cod_response='1',
            payment__subscription__starts_date__range=[start_month, end_month]
        )
        for operation in operations:
            ft = FinancialTransaction.objects.get(
                order_number=operation.payment.arc_order,
                transaction_type='Payment'
            )
            print(ft.order_id)
