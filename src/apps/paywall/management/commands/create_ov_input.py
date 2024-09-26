from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from sentry_sdk import capture_exception

from ...utils_siebel_input import SiebelSubscriptionSender
from apps.paywall.models import Operation, FinancialTransaction, Subscription


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def valid_create_ov(self, operation, date_operation):
        # retorna 1 si es el primer cambio de tarifa o es una primera venta(web)
        # retorna 0 otro caso
        try:
            if operation.payment.pa_origin == 'RECURRENCE':
                arc_id = operation.payment.subscription.arc_id
                nro_recurrence = Operation.objects.filter(payment__subscription__arc_id=arc_id,
                                                          payment__date_payment__lte=date_operation).count()

                if len(operation.plan.data['rates']) > 1:  # valida si hay promocion en el plan
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

            if len(operation.plan.data['rates']) > 1:  # valida si hay promocion en el plan
                first_change_rate = int(operation.plan.data['rates'][0]['durationCount']) + 1
                if nro_recurrence == first_change_rate:  # primer cambio de tarifa
                    return 1
                else:
                    return 0
            else:
                return 0
        else:
            return 0

    def handle(self, *args, **options):
        """
        list_subscriptions = ['2340797961937327', '3003826307500218', '6164383837167315', '3624720637372103', '3487890431010461',
         '7364527341090878', '1687710875315917', '1930628619552609', '6657177220475049', '6937755027000617',
         '1661446800151539', '8629051341931056', '8700636338583259', '3752732716363940', '5698180553543034',
         '6044762962143990', '6876311510976850', '4231818569267421', '1263171562434550', '8611055149172798',
         '538298809984049', '1959444103114791', '6622819652213395', '1780507881354760', '1588169777338667',
         '6468327161261155', '4021605958448155', '776938863806532']
        """
        list_subscriptions = ['4021605958448155', '776938863806532']

        operation_list = Operation.objects.filter(
            payment__subscription__arc_id__in=list_subscriptions,
            ope_amount__gte=5,
            siebel_hits__lte=2,
            payment__pa_origin='WEB'
        ).order_by('payment__date_payment')

        print(operation_list.query)
        print(operation_list)
        for operation in operation_list:
            siebel_client = SiebelSubscriptionSender(
                operation, self.first_rate_change(operation, operation.payment.date_payment))

            try:
                print(operation.payment.subscription.arc_id)
                siebel_client.send_subscription()
            except Exception:
                capture_exception()











