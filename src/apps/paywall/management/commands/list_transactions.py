from django.core.management.base import BaseCommand
from apps.paywall.models import Operation, FinancialTransaction, Subscription
from apps.siebel.models import LoadTransactionsIdSiebel, SiebelConfirmationPayment, LogSiebelOv
from datetime import date, timedelta, datetime
from django.utils.encoding import smart_str
import csv
from django.utils.timezone import get_default_timezone


class Command(BaseCommand):
    help = 'Ejecuta el comando'
    # python manage.py report_igv --lista_payments 1 --opcion comando

    def add_arguments(self, parser):
        parser.add_argument('--start_date', nargs='?', type=str)
        parser.add_argument('--end_date', nargs='?', type=str)

    def start_day(self, start_date):
        starts = datetime.combine(
            start_date,
            datetime.min.time()
        )
        return get_default_timezone().localize(starts)

    def end_day(self, end_date):
        ends = datetime.combine(
            end_date,
            datetime.max.time()
        )
        return get_default_timezone().localize(ends)

    def local_format(self, _date):
        try:
            if not isinstance(_date, datetime):
                return ''

            _date = _date.astimezone(
                get_default_timezone()
            )

            _date = _date.replace(tzinfo=None)

            return _date
        except Exception as e:
            return ''
        except SystemExit:
            return ''

    def handle(self, *args, **options):

        start_date = options.get('start_date')
        start_date = self.start_day(datetime.strptime(start_date, '%d-%m-%Y'))
        end_date = options.get('end_date')
        end_date = self.end_day(datetime.strptime(end_date, '%d-%m-%Y'))
        """
        log_ov = LogSiebelOv.objects.filter(
            created__range=[start_date, end_date],
            operation__payment__subscription__delivery__isnull=False
        )
        """
        """
        op = Operation.objects.filter(
            payment__date_payment__range=[start_date, end_date],
            payment__subscription__delivery__isnull=False
        )
        """
        op = Operation.objects.filter(
            payment__date_payment__lte=start_date,
            payment__subscription__date_renovation__gte=start_date,
        ).exclude(payment__subscription__date_anulled__lte=start_date)

        print(op.count())
        with open('/tmp/transacciones_junio.csv', 'a') as csvFile:
            writer = csv.writer(csvFile)
            for obj_op in op.iterator():
                if obj_op.payment.subscription.starts_date:
                    subscription_start = self.local_format(obj_op.payment.subscription.starts_date)
                else:
                    subscription_start = ''

                if obj_op.payment.subscription.date_anulled:
                    subscription_end = self.local_format(obj_op.payment.subscription.date_anulled)
                else:
                    subscription_end = ''

                if obj_op.payment.date_payment:
                    payment_date = self.local_format(obj_op.payment.date_payment)
                else:
                    payment_date = ''

                try:
                    writer.writerow([
                        smart_str(obj_op.payment.subscription.delivery),
                        smart_str(obj_op.payment.payu_transaction),
                        smart_str(payment_date),
                        smart_str(obj_op.payment.subscription.get_state_display()),
                        smart_str(subscription_start),
                        smart_str(subscription_end)
                    ])
                except Exception as e:
                    print(e)
                    print(obj_op)
                    pass
            csvFile.close()
            print('end')
