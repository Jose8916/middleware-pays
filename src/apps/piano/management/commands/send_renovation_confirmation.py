# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from apps.piano.constants import TERMS_EXCLUDE, LIST_ENABLE_SEND_SIEBEL
from apps.piano.constants import LIST_EMAIL_SENDER
from sentry_sdk import capture_exception
from apps.paywall.shortcuts import render_send_email

from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, SiebelConfirmationPayment
from apps.piano.utils.siebel_confirmation_renovation import SiebelConciliationSender
from apps.piano.models import Transaction, TransactionsWithNewDate, SubscriptionMatchArcPiano, BlockedSubscriptions, \
    RenovationPiano
from apps.paywall.models import Partner, Operation as OperationArc
import csv
import time
from apps.paywall.arc_clients import SalesClient
from datetime import datetime, timedelta
from django.utils import formats, timezone


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def add_arguments(self, parser):
        parser.add_argument('--test_mode', nargs='?', type=str)
        parser.add_argument('--print_log', nargs='?', type=str)
        parser.add_argument('--filter_elements', nargs='?', type=str)
        parser.add_argument('--list_elements', nargs='?', type=str)

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
            if count_ == 1 and operation.payu_transaction_id == transaction_obj.payu_transaction_id \
                    and transaction_obj.initial_payment is False:
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

    def validation(self, operation):
        try:
            state_transaction = operation.siebel_renovation.state
        except:
            state_transaction = ''

        if SubscriptionMatchArcPiano.objects.filter(
                subscription_id_piano=operation.subscription.subscription_id
        ).exists():
            try:
                obj_subs_match = SubscriptionMatchArcPiano.objects.get(
                    subscription_id_piano=operation.subscription.subscription_id
                )
                count_subs_match = SubscriptionMatchArcPiano.objects.filter(
                    subscription_id_arc=obj_subs_match.subscription_id_arc
                ).count()
                if count_subs_match == 1:
                    pass
                else:
                    return False
            except Exception as e:
                return False

        try:
            term_id_ = operation.term.term_id
        except:
            term_id_ = ''

        if state_transaction is True:
            return False

        # se excluye Plan Universitario, cross, Digital CYBERWOW2021 Trimestral Web
        if term_id_ in TERMS_EXCLUDE:
            if operation.subscription.subscription_id in LIST_ENABLE_SEND_SIEBEL:
                return True
            else:
                return False
        else:
            return True

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

    def siebel_attempts(self, operation, attempts):
        if operation.siebel_renovation:
            if operation.siebel_renovation.siebel_hits <= int(attempts):
                return True
            else:
                return False
        else:
            return True

    def validate_repeat_send(self, operation):
        if RenovationPiano.objects.filter(payu_transaction_id=operation.payu_transaction_id, state=True).exists():
            return False
        return True

    def handle(self, *args, **options):
        """
            - Servicio que envia las renovaciones
            - forma de envio python3 manage.py send_renovation_confirmation --test_mode 1
        """
        print('Inicio del comando. ')
        if options.get('list_elements', ''):
            list_elements_to_send = []
            list_elements = options.get('list_elements', '')
            if list_elements.find('*') == -1:
                list_elements_to_send = [list_elements]
            else:
                list_elements_to_send = list_elements.split('*')

        test_mode = True if options.get('test_mode', '') == '1' else False
        config_siebel = SiebelConfiguration.objects.get(state=True)

        list_subscription_send = []
        list_ext_tx_id_send = []
        list_exclude = []
        list_error_type = []
        if not config_siebel.blocking and not config_siebel.queue_piano_vouchers:
            config_siebel.queue_piano_vouchers = True
            config_siebel.save()

            transanciones_objects = TransactionsWithNewDate.objects.all()
            for obj_transaction in transanciones_objects:
                list_subscription_send.append(obj_transaction.subscription_id_piano)
                list_ext_tx_id_send.append(obj_transaction.external_tx_id)

            blocked_subscriptions = BlockedSubscriptions.objects.all()
            for blocked_subscription in blocked_subscriptions:
                list_exclude.append(blocked_subscription.subscription_id_piano)

            operation_list = Transaction.objects.filter(
                amount__gte=4,
                subscription__payment_profile__siebel_entecode__isnull=False,
                subscription__payment_profile__siebel_entedireccion__isnull=False
            ).exclude(initial_payment=True).exclude(siebel_renovation__state=True) \
                .exclude(siebel_payment__cod_response=True) \
                .exclude(siebel_payment__siebel_response__contains='Correcto') \
                .exclude(siebel_payment__siebel_response__contains='ya se encuentra registrado') \
                .exclude(subscription__locked=True) \
                .exclude(block_sending=True) \
                .exclude(devolution=True).exclude(subscription_id_str__in=list_exclude)

            if options.get('filter_elements', ''):
                operation_list = operation_list[:int(options.get('filter_elements'))]
            elif options.get('list_elements', ''):
                operation_list = operation_list.filter(subscription_id_str__in=list_elements_to_send)
            else:
                operation_list = operation_list.order_by('payment_date')

            if options.get('print_log', ''):
                with open('/tmp/log_ext_tx_id.csv', 'a', encoding="utf-8") as csvFile:
                    writer = csv.writer(csvFile)
                    for operation in operation_list:
                        writer.writerow([operation.external_tx_id])

            for operation in operation_list:
                error_tye = None
                if operation.subscription.delivery and self.validation(operation) and \
                        self.siebel_attempts(operation, config_siebel.conciliation_attempts):
                    if self.valid_last_payment_arc(
                            operation.subscription.subscription_id) and self.valid_last_payment(
                        operation) and not SiebelConfirmationPayment.objects.filter(
                            num_liquidacion=operation.payu_transaction_id).exists():  # verifica que aya un pago anterior
                        if self.validate_repeat_send(operation):
                            siebel_client = SiebelConciliationSender(operation, test_mode)
                            try:
                                print('Iniciando external_tx_id: {operation_id}'.format(
                                    operation_id=operation.external_tx_id))
                                if operation.external_tx_id in list_ext_tx_id_send:
                                    try:
                                        obj_t = TransactionsWithNewDate.objects.get(
                                            external_tx_id=operation.external_tx_id,
                                            subscription_id_piano=operation.subscription.subscription_id
                                        )
                                    except:
                                        continue
                                    error_type = siebel_client.renovation_send(obj_t.access_from, obj_t.access_to)
                                else:
                                    error_type = siebel_client.renovation_send(None, None)
                            except Exception:
                                capture_exception()

                tz = timezone.get_current_timezone()
                if error_tye and operation.payment_date >= datetime.strptime('12/12/2022', '%m/%d/%Y').astimezone(tz):
                    list_error_type.append(error_type)

            if list_error_type:
                try:
                    partner = Partner.objects.get(partner_code=self.brand)
                except Exception:
                    partner = None
                if partner:
                    from_email = '{name_sender} <{direction_sender}>'.format(
                        name_sender=partner.partner_name,
                        direction_sender=partner.transactional_sender
                    )
                else:
                    from_email = None

                render_send_email(
                    template_name='mailings/error.html',
                    subject=('[Test]' if settings.ENVIRONMENT == 'test' else '[Production]') + ' Siebel no renovo',
                    to_emails=LIST_EMAIL_SENDER,
                    from_email=from_email,
                    context={
                        'error': str(list_error_type),
                    }
                )
            config_siebel.queue_piano_vouchers = False
            config_siebel.save()
        print('Termino la ejecucion del comando')
