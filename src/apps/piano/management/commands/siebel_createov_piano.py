from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.paywall.shortcuts import render_send_email
from apps.paywall.models import Partner
from apps.piano.constants import LIST_EMAIL_SENDER
from sentry_sdk import capture_exception

from apps.piano.utils_siebel import SiebelSubscriptionSender
from apps.paywall.models import Operation, FinancialTransaction, Subscription
from apps.piano.piano_clients import VXClient
from apps.siebel.models import SiebelConfiguration, ReasonExclude
from apps.piano.models import Transaction, BlockedSubscriptions
from datetime import datetime, timedelta
from apps.piano.constants import TERMS_EXCLUDE, LIST_ENABLE_SEND_SIEBEL
from django.utils import timezone


class Command(BaseCommand):
    help = 'Crea las ordenes de venta de siebel.'
    """
        python3 manage.py siebel_createov_piano --test_mode 1
        python3 manage.py siebel_createov_piano --filter_elements 1
        python3 manage.py siebel_createov_piano --id_transaction nro
    """

    def add_arguments(self, parser):
        parser.add_argument('--test_mode', nargs='?', type=str)
        parser.add_argument('--filter_elements', nargs='?', type=str)
        parser.add_argument('--id_transaction', nargs='?', type=str)

    def get_delivery(self, operation):
        try:
            return operation.subscription.delivery
        except:
            return ''

    def siebel_attempts(self, operation, attempts):
        if operation.siebel_sale_order:
            if operation.siebel_sale_order.siebel_hits <= int(attempts):
                return True
            else:
                return False
        else:
            return True

    def valid_fields(self, operation):
        if operation.term and operation.access_from and not self.get_delivery(operation):
            if operation.term.product:
                if operation.term.product.siebel_name and operation.term.product.siebel_code \
                        and operation.term.net_price_first_payment:
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

    def handle(self, *args, **options):
        test_mode = True if options.get('test_mode', '') == '1' else False
        list_exclude = []
        config_siebel = SiebelConfiguration.objects.get(state=True)
        if not config_siebel.blocking and not config_siebel.queue_piano_delivery:
            config_siebel.queue_piano_delivery = True
            config_siebel.save()

            blocked_subscriptions = BlockedSubscriptions.objects.all()
            for blocked_subscription in blocked_subscriptions:
                list_exclude.append(blocked_subscription.subscription_id_piano)

            if options.get('id_transaction', ''):
                operation_list = Transaction.objects.filter(
                    external_tx_id=options.get('id_transaction', '')
                )
            else:
                operation_list = Transaction.objects.filter(
                    initial_payment=True,
                    amount__gte=4,
                    subscription__delivery__isnull=True
                )
                operation_list = operation_list.exclude(subscription__payment_profile__siebel_entecode=None)
                operation_list = operation_list.exclude(subscription__payment_profile__siebel_name=None)
                operation_list = operation_list.exclude(block_sending=True)
                operation_list = operation_list.exclude(subscription__locked=True)
                operation_list = operation_list.exclude(subscription_id_str__in=list_exclude)
                if options.get('filter_elements', ''):
                    operation_list = operation_list[:int(options.get('filter_elements'))]

            list_delivery_error = []
            for operation in operation_list:
                delivery_error = None
                if self.valid_fields(operation) and self.siebel_attempts(operation, config_siebel.ov_attempts):
                    if operation.term.app_id == settings.PIANO_APPLICATION_ID['gestion']:
                        brand = 'gestion'
                    elif operation.term.app_id == settings.PIANO_APPLICATION_ID['elcomercio']:
                        brand = 'elcomercio'
                    else:
                        brand = ''

                    subscription = VXClient().get_subscription(brand, operation.subscription_id_str)
                    siebel_client = SiebelSubscriptionSender(operation, subscription.get('subscription'), test_mode, brand)
                    try:
                        print('Inicia proceso de envio, con external id: {external_id}'.format(
                            external_id=operation.external_tx_id))
                        delivery_error = siebel_client.send_subscription()
                    except Exception:
                        capture_exception()

                    tz = timezone.get_current_timezone()
                    if delivery_error and operation.subscription.start_date >= datetime.strptime('12/12/2022', '%m/%d/%Y').astimezone(tz):
                        list_delivery_error.append(delivery_error)

            if list_delivery_error:
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
                    subject=('[Test]' if settings.ENVIRONMENT == 'test' else '[Production]') + ' No creo delivery',
                    to_emails=LIST_EMAIL_SENDER,
                    from_email=from_email,
                    context={
                        'error': 'no creo delivery ' + str(list_delivery_error),
                    }
                )
            config_siebel.queue_piano_delivery = False
            config_siebel.save()
        print('Termino ejecucion de comando')

