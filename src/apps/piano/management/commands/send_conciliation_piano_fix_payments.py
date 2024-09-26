# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from apps.piano.constants import TERMS_EXCLUDE, LIST_ENABLE_SEND_SIEBEL
from sentry_sdk import capture_exception

from apps.paywall.models import Operation as OperationArc
from apps.piano.models import Transaction, BlockedSubscriptions, SubscriptionMatchArcPiano, SubscriptionToFix
from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, SiebelConfirmationPayment, \
    SubscriptionExclude
from ...utils_siebel import SiebelConciliationSender


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def add_arguments(self, parser):
        parser.add_argument('--first_sale', nargs='?', type=str)
        parser.add_argument('--test_mode', nargs='?', type=str)
        parser.add_argument('--filter_elements', nargs='?', type=str)

    def valid_fields(self, operation):
        if operation.term and operation.access_from and operation.subscription:
            if operation.term.product and operation.subscription.delivery:
                try:
                    term_id_ = operation.term.term_id
                except:
                    term_id_ = ''
                # se excluye Plan Universitario, cross, Digital CYBERWOW2021 Trimestral Web
                if term_id_ in TERMS_EXCLUDE:
                    if operation.subscription.subscription_id in LIST_ENABLE_SEND_SIEBEL:
                        return 1
                    else:
                        return 0

                if operation.amount:
                    return 1
                else:
                    print('No cumple las condicines, sin amount ex_id: {external_id}'.format(external_id=operation.external_tx_id))
                    return 0
            else:
                print('No cumple las condicines, sin producto o delivery ex_id: {external_id}'.format(external_id=operation.external_tx_id))
                return 0
        else:
            print('No cumple las condicines, sin termino sin acceso o suscripcion ex_id: {external_id}'.format(external_id=operation.external_tx_id))
            return 0

    def valid_last_payment_arc(self, piano_subs_id):
        """
            verifica que la anterior un pago anterior
        """
        if SubscriptionMatchArcPiano.objects.filter(subscription_id_piano=piano_subs_id).exists():
            try:
                obj_subs = SubscriptionMatchArcPiano.objects.get(subscription_id_piano=piano_subs_id)
            except Exception as e:
                return False
            operations_objs = OperationArc.objects.filter(
                payment__subscription__arc_id=obj_subs.subscription_id_arc
            ).order_by(
                'payment__date_payment'
            ).last()

            if operations_objs.conciliation_cod_response == "1":
                return True
            else:
                return False
        else:
            return True

    def confirmation_notification(self, operation, payu_transaction):
        if operation and payu_transaction:
            try:
                confirmation_payment = SiebelConfirmationPayment.objects.get(
                    cod_delivery=operation.subscription.delivery,
                    num_liquidacion=payu_transaction
                )
            except Exception as e:
                print(e)
                print(operation.subscription.delivery)
                confirmation_payment = None
        else:
            confirmation_payment = None
        return confirmation_payment

    def valid_last_payment(self, operation):
        """
            verifica que aya un pago anterior
        """
        transactions_objs = Transaction.objects.filter(
            subscription_id_str=operation.subscription_id_str
        ).exclude(
            devolution=True
        ).order_by(
            'payment_date'
        )
        # if transactions_objs.count() == 1:
        #    return True

        count_ = 1
        for transaction_obj in transactions_objs:
            if count_ == 1 and operation.payu_transaction_id == transaction_obj.payu_transaction_id:
                return True
            else:
                count_ = count_ + 1

            if transaction_obj.payu_transaction_id == operation.payu_transaction_id:
                try:
                    if last_object.siebel_payment.cod_response:
                        return True
                    else:
                        return False
                except:
                    return False
            last_object = transaction_obj

        return False

    def handle(self, *args, **options):
        """
            - Servicio para la correccion de las devoluciones, se quita la validacion de recepcion de comprobantes
            - Servicio que envia los pagos a siebel
            - forma de envio python3 manage.py send_conciliation_piano --first_sale 1 --test_mode 1
        """
        test_mode = True if options.get('test_mode', '') == '1' else False
        config_siebel = SiebelConfiguration.objects.get(state=True)
        list_exclude = []
        list_subscription_to_fix = []
        list_transaction_to_fix = []
        fix_subscriptions = SubscriptionToFix.objects.all()
        for fix_subscription in fix_subscriptions:
            list_subscription_to_fix.append(fix_subscription.subscription_id)
            list_transaction_to_fix.append(fix_subscription.payu_transaction_id)
        print(list_subscription_to_fix)
        print(list_transaction_to_fix)
        if options.get('first_sale') == '1':
            first_sale = True
        else:
            first_sale = False

        if not config_siebel.blocking:
            blocked_subscriptions = BlockedSubscriptions.objects.all()
            for blocked_subscription in blocked_subscriptions:
                list_exclude.append(blocked_subscription.subscription_id_piano)

            operation_list = Transaction.objects.filter(
                subscription__payment_profile__siebel_entecode__isnull=False,
                subscription__payment_profile__siebel_entedireccion__isnull=False,
                amount__gte=4,
                initial_payment=first_sale,
                subscription_id_str__in=list_subscription_to_fix,
                payu_transaction_id__in=list_transaction_to_fix,
            )
            operation_list = operation_list.exclude(siebel_payment__cod_response=True)
            operation_list = operation_list.exclude(siebel_payment__siebel_response__contains='ya se encuentra registrado')
            operation_list = operation_list.exclude(subscription__delivery__isnull=True)
            operation_list = operation_list.exclude(subscription__locked=True)
            operation_list = operation_list.exclude(devolution=True)
            operation_list = operation_list.exclude(block_sending=True)
            operation_list = operation_list.exclude(subscription_id_str__in=list_exclude)

            # if not first_sale:
            #    operation_list = operation_list.filter(siebel_renovation__state=True)

            if options.get('filter_elements', ''):
                operation_list = operation_list[:int(options.get('filter_elements'))]

            for operation in operation_list:
                print(operation.external_tx_id)
                print(self.valid_fields(operation))
                print(self.valid_last_payment_arc(operation.subscription.subscription_id))
                print(self.valid_last_payment(operation))
                print('-----------')
                if self.valid_fields(operation):
                    if self.valid_last_payment_arc(operation.subscription.subscription_id) and\
                            self.valid_last_payment(operation):

                        siebel_client = SiebelConciliationSender(operation)
                        try:
                            print('Inicia proceso de envio, con external id: {external_id}'.format(
                                external_id=operation.external_tx_id))
                            siebel_client.send_conciliation_without_vouchers(None,  test_mode)
                        except Exception:
                            capture_exception()

        print('Termino la ejecucion del comando')
