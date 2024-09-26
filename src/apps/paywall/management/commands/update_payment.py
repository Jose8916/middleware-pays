from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.arcsubs.utils import timestamp_to_datetime
from apps.paywall.models import Payment, FinancialTransaction


class Command(BaseCommand):
    help = 'Ejecuta el comando'
    # python update_payment --transactionid 1

    def add_arguments(self, parser):
        parser.add_argument('--transactionid', nargs='?', type=str)

    def handle(self, *args, **options):
        if options.get('transactionid'):
            payments = Payment.objects.filter(Q(payu_transaction__isnull=True) | Q(payu_transaction=''))
            count = 0
            for payment in payments.iterator():
                try:
                    transaction_obj = FinancialTransaction.objects.get(
                        order_number=payment.arc_order,
                        transaction_type='Payment'
                    )
                except Exception:
                    transaction_obj = None

                if transaction_obj:
                    count = count + 1
                    payment.payu_transaction = transaction_obj.transaction_id
                    payment.save()
                    print(transaction_obj.transaction_id)
            return 'Se actualizaron registros: ' + str(count)
        else:
            payments = Payment.objects.all()
            count = 0
            for payment in payments:
                try:
                    if payment.data:
                        transaction_date_local = payment.data['payments'][0]['financialTransactions'][0]['transactionDate']
                        if not payment.transaction_date:
                            payment.transaction_date = timestamp_to_datetime(transaction_date_local)
                            payment.save()
                            count = count + 1
                except Exception as e:
                    print(e)
            return 'Se actualizaron registros: ' + str(count)
