from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from sentry_sdk import capture_exception

from ...utils_siebel import SiebelSubscriptionSender
from apps.paywall.models import Operation, FinancialTransaction, Subscription
from apps.paywall.arc_clients import SalesClient
from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, Rate, SubscriptionExclude
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Ejecuta el comando'
    """
        python3 manage.py siebel_createov --load_transactions_id 1 --operation_type web  #carga los transactions id del admin
        python3 manage.py siebel_createov --subscription_id 6269097765365606 #solo para tipo web
        python3 manage.py siebel_createov --type recurrence
        python3 manage.py siebel_createov --type web
    """

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

    def first_rate_change(self, operation, date_operation):
        # retorna 1 si es el primer cambio de tarifa
        # retorna 0 si no es el primer cambio de tarifa

        if operation.payment.pa_origin == 'RECURRENCE':
            arc_id = operation.payment.subscription.arc_id
            nro_recurrence = Operation.objects.filter(payment__subscription__arc_id=arc_id,
                                                      payment__date_payment__lte=date_operation).count()

            try:
                rate_obj = Rate.objects.get(plan=self.operation.plan, type=1)  # 1 es para promocion
                duration_rate = int(rate_obj.duration) + 1
            except Exception:
                duration_rate = None

            if duration_rate:
                if nro_recurrence == duration_rate and int(rate_obj.rate_total) == 0:
                    return 1
                else:
                    return 0
            elif len(operation.plan.data['rates']) > 1:  # valida si hay promocion en el plan
                first_change_rate = int(operation.plan.data['rates'][0]['durationCount']) + 1
                if nro_recurrence == first_change_rate:  # primer cambio de tarifa
                    return 1
                else:
                    return 0
            else:
                return 0
        else:
            return 0

    def add_arguments(self, parser):
        parser.add_argument('--subscription_id', nargs='?', type=str)
        parser.add_argument('--load_transactions_id', nargs='?', type=str)
        parser.add_argument('--operation_type', nargs='?', type=str)
        parser.add_argument('--inicio', nargs='?', type=str)
        parser.add_argument('--type', nargs='?', type=str)
        parser.add_argument('--test', nargs='?', type=str)
        parser.add_argument('--fecha_fin', nargs='?', type=str)

    def handle(self, *args, **options):
        list_reason = []
        list_subscription_exclude = []

        config_siebel = SiebelConfiguration.objects.get(state=True)
        if not config_siebel.blocking:
            reasons = ReasonExclude.objects.all()
            for reason in reasons:
                list_reason.append(str(reason.reason))

            subs_exclude = SubscriptionExclude.objects.all()
            for subs in subs_exclude:
                list_subscription_exclude.append(str(subs.subscription))

            if options.get('inicio'):
                ahora = datetime.utcnow() - timedelta(days=67)
            else:
                ahora = datetime.utcnow()

            last_month = ahora - timedelta(days=int(config_siebel.days_ago))

            if options.get('fecha_fin'):
                fecha_fin = int(options.get('fecha_fin'))
                ahora = datetime.utcnow() - timedelta(days=fecha_fin)
            print([last_month, ahora])
            if options.get('load_transactions_id') and options.get('operation_type'):
                type_operation = options.get('operation_type')
                load_transactions_id_siebel = LoadTransactionsIdSiebel.objects.all()
                for transaction in load_transactions_id_siebel:
                    transactions = transaction.transaction_id
                    list_transactions = transactions.splitlines()

                operation_list = Operation.objects.filter(
                    payment__payment_financial_transaction__transaction_id__in=list_transactions,
                    payment__subscription__delivery__isnull=True,
                    ope_amount__gte=4
                ).exclude(payment_profile__siebel_entecode=None)\
                    .exclude(payment_profile__siebel_name=None)

            elif options.get('subscription_id'):
                type_operation = 'web'  # recurrence
                operation_list = Operation.objects.filter(
                    payment__subscription__arc_id=options.get('subscription_id'),
                    siebel_delivery__isnull=True,
                    siebel_hits__lte=int(config_siebel.ov_attempts),
                    ope_amount__gte=5,
                    payment__pa_origin='WEB'
                ).exclude(
                    payment_profile__siebel_entecode=None,
                    payment_profile__siebel_name=None
                )
            elif options.get('type') == 'web':
                type_operation = 'web'  # recurrence
                operation_list = Operation.objects.filter(
                    payment__subscription__delivery__isnull=True,
                    siebel_hits__lte=int(config_siebel.ov_attempts),
                    ope_amount__gte=4,
                    payment__pa_origin='WEB',
                    created__range=[last_month, ahora]
                ).exclude(payment_profile__siebel_entecode=None) \
                    .exclude(payment_profile__siebel_name=None)

            elif options.get('type') == 'recurrence':
                type_operation = 'recurrence'  # recurrence
                operation_list = Operation.objects.filter(
                    payment__subscription__delivery__isnull=True,
                    siebel_hits__lte=int(config_siebel.ov_attempts),
                    ope_amount__gte=5,
                    created__range=[last_month, ahora],
                    payment__pa_origin='RECURRENCE'
                ).exclude(payment_profile__siebel_entecode=None)\
                    .exclude(payment_profile__siebel_name=None)

            for reason in list_reason:
                operation_list = operation_list.exclude(payment__subscription__motive_anulled__contains=reason)

            for subs_to_exclude in list_subscription_exclude:
                operation_list = operation_list.exclude(payment__subscription__arc_id=int(subs_to_exclude))

            operation_list = operation_list.order_by('payment__date_payment')
            print('cantidad de registros' + str(operation_list.count()))
            print(operation_list)
            for operation in operation_list:
                enviar = False
                delivery_count = Operation.objects.filter(
                    payment__subscription=operation.payment.subscription,
                ).exclude(siebel_delivery__isnull=True).count()

                if delivery_count < 1:
                    try:
                        obj_financial_transaction = FinancialTransaction.objects.get(
                            order_number=operation.payment.arc_order,
                            transaction_type='Payment'
                        )
                    except Exception as e:
                        obj_financial_transaction = ''
                        print(e)

                    if obj_financial_transaction:
                        if obj_financial_transaction.transaction_id:
                            if not SalesClient().has_a_refund(operation.payment.partner.partner_code, operation.payment.arc_order):
                                if type_operation == 'web':
                                    siebel_client = SiebelSubscriptionSender(
                                        operation, 0, False)
                                    enviar = True
                                elif type_operation == 'recurrence':
                                    valid_lst_payment = self.valid_last_payment(operation)
                                    siebel_client = SiebelSubscriptionSender(
                                        operation, valid_lst_payment, False)

                                    if valid_lst_payment:
                                        enviar = True

                                try:
                                    if type_operation and enviar:
                                        if not options.get('test', 0):
                                            print('Inicio de envio operacion: ' + str(operation.id))
                                            print('Inicio de envio transaccion: ' + str(
                                                obj_financial_transaction.transaction_id))
                                            siebel_client.send_subscription()
                                except Exception:
                                    capture_exception()
