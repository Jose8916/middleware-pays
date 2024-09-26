# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from apps.piano.constants import TERMS_EXCLUDE, LIST_ENABLE_SEND_SIEBEL
from sentry_sdk import capture_exception
from apps.paywall.shortcuts import render_send_email
from apps.piano.constants import LIST_EMAIL_SENDER
from apps.paywall.models import Partner
from apps.piano.models import Transaction, BlockedSubscriptions
from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, SiebelConfirmationPayment, \
    SubscriptionExclude
from ...utils_siebel import SiebelConciliationSender
from datetime import datetime, timedelta
from django.utils import timezone


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
                    print('No cumple las condicines, ex_id: {external_id}'.format(external_id=operation.external_tx_id))
                    return 0
            else:
                print('No cumple las condicines, ex_id: {external_id}'.format(external_id=operation.external_tx_id))
                return 0
        else:
            print('No cumple las condicines, ex_id: {external_id}'.format(external_id=operation.external_tx_id))
            return 0

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

    def siebel_attempts(self, operation, attempts):
        if operation.siebel_payment:
            if operation.siebel_payment.siebel_hits <= int(attempts):
                return True
            else:
                return False
        else:
            return True

    def handle(self, *args, **options):
        """
            - Servicio que envia los pagos a siebel
            - forma de envio python3 manage.py send_conciliation_piano --first_sale 1 --test_mode 1
        """
        test_mode = True if options.get('test_mode', '') == '1' else False
        config_siebel = SiebelConfiguration.objects.get(state=True)
        list_exclude = []
        if options.get('first_sale') == '1':
            first_sale = True
        else:
            first_sale = False

        if not config_siebel.blocking and not config_siebel.queue_piano_conciliation:
            config_siebel.queue_piano_conciliation = True
            config_siebel.save()

            blocked_subscriptions = BlockedSubscriptions.objects.all()
            for blocked_subscription in blocked_subscriptions:
                list_exclude.append(blocked_subscription.subscription_id_piano)

            operation_list = Transaction.objects.filter(
                subscription__payment_profile__siebel_entecode__isnull=False,
                subscription__payment_profile__siebel_entedireccion__isnull=False,
                amount__gte=4,
                initial_payment=first_sale
            )
            operation_list = operation_list.exclude(siebel_payment__cod_response=True)
            operation_list = operation_list.exclude(siebel_payment__siebel_response__contains='ya se encuentra registrado')
            operation_list = operation_list.exclude(subscription__delivery__isnull=True)
            operation_list = operation_list.exclude(subscription__locked=True)
            operation_list = operation_list.exclude(devolution=True)
            operation_list = operation_list.exclude(block_sending=True)
            operation_list = operation_list.exclude(subscription_id_str__in=list_exclude)

            if not first_sale:
                operation_list = operation_list.filter(siebel_renovation__state=True)

            if options.get('filter_elements', ''):
                operation_list = operation_list[:int(options.get('filter_elements'))]
            list_error_message = []
            for operation in operation_list:
                error_message = None
                if first_sale:
                    payu_transaction = 'VENTA'
                else:
                    payu_transaction = operation.payu_transaction_id

                confirmation_payment = self.confirmation_notification(operation, payu_transaction)
                if confirmation_payment and self.valid_fields(operation) and \
                        self.siebel_attempts(operation, config_siebel.conciliation_attempts):
                    siebel_client = SiebelConciliationSender(operation)
                    try:
                        print('Inicia proceso de envio, con external id: {external_id}'.format(
                            external_id=operation.external_tx_id))
                        error_message = siebel_client.send_conciliation(confirmation_payment,  test_mode)
                    except Exception:
                        capture_exception()

                tz = timezone.get_current_timezone()
                if error_message and operation.payment_date >= datetime.strptime('12/12/2022', '%m/%d/%Y').astimezone(tz):
                    list_error_message.append(error_message)

            if list_error_message:
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
                    subject=('[Test]' if settings.ENVIRONMENT == 'test' else '[Production]') + ' Error en el pago',
                    to_emails=LIST_EMAIL_SENDER,
                    from_email=from_email,
                    context={
                        'error': str(list_error_message),
                    }
                )

            config_siebel.queue_piano_conciliation = False
            config_siebel.save()
        print('Termino la ejecucion del comando')
