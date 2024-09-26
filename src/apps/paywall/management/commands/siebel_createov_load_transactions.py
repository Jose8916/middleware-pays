from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from sentry_sdk import capture_exception

from ...utils_siebel import SiebelSubscriptionSender
from apps.paywall.models import Operation, FinancialTransaction, Subscription
from apps.paywall.arc_clients import SalesClient
from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, Rate
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Ejecuta el comando'
    """
        python3 manage.py siebel_createov_load_transactions --load_transactions_id 1   #carga los transactions id del admin
        python3 manage.py siebel_createov --subscription_id 3604624180559851 #crea la ov de la siguiente suscription_id
    """

    def valid_last_payment(self, operation):
        """
            verifica que en el anterior pago no se aya creado el delivery
        """
        if operation.payment.subscription.delivery:
            return False

        # ------------------------------------------------------------------------------------------------------------#
        # ----------- Tarea pendiente llenar el campo delivery en suscripcion para eliminar las lineas de abajo.......#
        # ------------------------------------------------------------------------------------------------------------#

        operations_objs = Operation.objects.filter(
            payment__subscription__arc_id=operation.payment.subscription.arc_id
        ).order_by(
            'payment__date_payment'
        )

        count = 1
        total = operations_objs.count()

        for operation_obj in operations_objs:
            if total == 1 and not operation.siebel_delivery:
                return True

            if operation_obj.payment.arc_order == operation.payment.arc_order:
                if count > 1:
                    if last_object.siebel_delivery:
                        return False
                    elif not last_object.siebel_delivery:
                        return True
                elif count == 1 and operation_obj.ope_amount > 3 and not operation_obj.siebel_delivery:
                    return True

            last_object = operation_obj
            count = count + 1

    def valid_create_ov(self, operation, date_operation):
        """
            para que se envie la creacion de la OV debe ser de tipo web o recurrece(si es la anterior tarifa fue
            gratuita)

            retorna 1 si es el primer cambio de tarifa o es una primera venta(web)
            retorna 0 otro caso
        """
        try:
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
            elif operation.payment.pa_origin == 'WEB':
                return 1
            else:
                return 0
        except Exception as e:
            return 0

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

    def handle(self, *args, **options):
        list_reason = []
        config_siebel = SiebelConfiguration.objects.get(state=True)
        if not config_siebel.blocking:
            reasons = ReasonExclude.objects.all()
            for reason in reasons:
                list_reason.append(str(reason.reason))

            current_month = datetime.now().month
            ahora = datetime.utcnow()
            last_month = ahora - timedelta(days=int(config_siebel.days_ago))

            if options.get('load_transactions_id'):
                load_transactions_id_siebel = LoadTransactionsIdSiebel.objects.all()
                for transaction in load_transactions_id_siebel:
                    transactions = transaction.transaction_id
                    list_transactions = transactions.splitlines()

                operation_list = Operation.objects.filter(
                    payment__payment_financial_transaction__transaction_id__in=list_transactions,
                    ope_amount__gte=4
                ).exclude(payment_profile__siebel_entecode=None)\
                    .exclude(payment_profile__siebel_name=None)

                for reason in list_reason:
                    operation_list = operation_list.exclude(payment__subscription__motive_anulled__contains=reason)

                operation_list = operation_list.order_by('payment__date_payment')

            elif options.get('subscription_id'):
                operation_list = Operation.objects.filter(
                    payment__subscription__arc_id=options.get('subscription_id'),
                    siebel_delivery__isnull=True,
                    siebel_hits__lte=int(config_siebel.ov_attempts),
                    ope_amount__gte=5
                ).exclude(
                    payment_profile__siebel_entecode=None,
                    payment_profile__siebel_name=None
                ).order_by('payment__date_payment')
            else:
                if settings.ENVIRONMENT == 'test':
                    operation_list = Operation.objects.filter(
                        siebel_delivery__isnull=True,
                        siebel_hits__lte=int(config_siebel.ov_attempts),
                        ope_amount__gte=5,
                        created__range=[last_month, ahora]
                    ).exclude(payment_profile__siebel_entecode=None)\
                        .exclude(payment_profile__siebel_name=None)

                    for reason in list_reason:
                        operation_list = operation_list.exclude(payment__subscription__motive_anulled__contains=reason)

                    operation_list = operation_list.order_by('payment__date_payment')
                elif settings.ENVIRONMENT == 'production':
                    operation_list = Operation.objects.filter(
                        siebel_delivery__isnull=True,
                        siebel_hits__lte=int(config_siebel.ov_attempts),
                        ope_amount__gte=5,
                        created__range=[last_month, ahora]
                    ).exclude(payment_profile__siebel_entecode=None)\
                        .exclude(payment_profile__siebel_name=None)

                    for reason in list_reason:
                        operation_list = operation_list.exclude(payment__subscription__motive_anulled__contains=reason)

                    operation_list = operation_list.order_by('payment__date_payment')

            for operation in operation_list:
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
                        siebel_client = SiebelSubscriptionSender(operation, 0, True)

                        try:
                            print('operacion: ' + str(operation.id))
                            siebel_client.send_subscription()
                        except Exception:
                            capture_exception()
