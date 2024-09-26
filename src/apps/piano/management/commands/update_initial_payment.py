# -*- coding: utf-8 -*-
import csv
import time
from django.db.models import Min, Max
from django.core.management.base import BaseCommand
from apps.piano.models import Transaction, Term, Subscription, SubscriptionMatchArcPiano
from apps.paywall.shortcuts import render_send_email
from apps.siebel.models import SiebelConfirmationPayment
from apps.piano.constants import LIST_EMAIL_SENDER
from apps.piano.utils.utils_functions import get_start_subscription
from apps.paywall.models import Partner
from django.utils import formats, timezone
from apps.piano.utils_models import get_or_create_subscription, get_payment_profile
from django.conf import settings
from datetime import date, datetime, timedelta


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    # 'python3 manage.py update_initial_payment

    def add_arguments(self, parser):
        parser.add_argument('--fix_ec', nargs='?', type=str)
        parser.add_argument('--term_2_trimestral', nargs='?', type=str)

    def handle(self, *args, **options):
        """
            - actualiza el pago inicial de la suscripcion
        """
        fix_ec = options.get('fix_ec')
        if fix_ec:
            list_error = []
            transactions = Transaction.objects.filter(
                initial_payment=True,
                term__app_id=settings.PIANO_APPLICATION_ID['elcomercio']
            )
            for transaction in transactions.iterator():
                if transaction.term:
                    first_payment = Transaction.objects.filter(
                        subscription_id=transaction.subscription_id
                    ).order_by('access_from_date').first()
                    if transaction.external_tx_id == first_payment.external_tx_id:
                        if transaction.subscription.start_date >= get_start_subscription(transaction.term.app_id):
                            # transaction ok
                            pass
                        else:
                            list_error.append(transaction.subscription_id_str)
                            transaction.initial_payment = False
                    else:
                        print('otro tipo ' + str(transaction.subscription_id_str))
                        list_error.append(transaction.subscription_id_str)
                        transaction.initial_payment = False
                    transaction.save()
                else:
                    print('transaccion sin termino')

            time_stamp = str(int(datetime.timestamp(datetime.now())))
            with open('/tmp/list_suscriptions' + time_stamp + '.csv', 'a', encoding="utf-8") as csvFilewrite:
                writer = csv.writer(csvFilewrite)
                for item in list_error:
                    cantidad = Transaction.objects.filter(
                        subscription_id_str=item
                    ).count()
                    print(item + ' ' + str(cantidad))
                    writer.writerow([item, str(cantidad)])
            csvFilewrite.close()
        elif options.get('term_2_trimestral'):
            transactions = Transaction.objects.filter(term_identifier='TMGM0F7MK839')
            for transaction in transactions.iterator():
                if SubscriptionMatchArcPiano.objects.filter(
                    subscription_id_piano=transaction.subscription_id_str
                ).exists():
                    print(transaction.subscription_id_str)
                    transaction.initial_payment = False
                    transaction.save()
        else:
            transactions = Transaction.objects.filter(initial_payment__isnull=True)
            for transaction in transactions.iterator():
                if transaction.term:
                    first_payment = Transaction.objects.filter(
                        subscription_id_str=transaction.subscription_id_str
                    ).order_by('access_from_date').first()
                    if transaction.external_tx_id == first_payment.external_tx_id:
                        if transaction.subscription.start_date >= get_start_subscription(transaction.term.app_id):
                            transaction.initial_payment = True
                        else:
                            transaction.initial_payment = False
                    else:
                        transaction.initial_payment = False
                    transaction.save()
                else:
                    print('transaccion sin termino')

        ###  Actualiza el perfil de pago ####
        subscriptions = Subscription.objects.filter(payment_profile__isnull=True).exclude(payment_profile=False)
        for subscription in subscriptions:
            if subscription.app_id == settings.PIANO_APPLICATION_ID['gestion']:
                brand = 'gestion'
            elif subscription.app_id == settings.PIANO_APPLICATION_ID['elcomercio']:
                brand = 'elcomercio'
            else:
                brand = ''
            if brand:
                subscription.payment_profile = get_payment_profile(subscription.uid, brand, subscription)
                subscription.save()

        # para renovaciones
        list_error_message = []
        transactions = Transaction.objects.filter(
            initial_payment=False,
            siebel_renovation__state=True,
            payment_date=date.today() - timedelta(days=2)
        )
        for transaction in transactions:
            if not SiebelConfirmationPayment.objects.filter(num_liquidacion=transaction.payu_transaction_id).exists():
                list_error_message.append(transaction.payu_transaction_id)

        transactions = Transaction.objects.filter(
            initial_payment=True,
            subscription__delivery__isnull=False,
            payment_date=date.today() - timedelta(days=2)
        )
        for transaction in transactions:
            if not SiebelConfirmationPayment.objects.filter(
                    num_liquidacion='VENTA',
                    cod_delivery=transaction.subscription.delivery
            ).exists():
                list_error_message.append(transaction.payu_transaction_id)

        if len(list_error_message) > 250:
            try:
                partner = Partner.objects.get(partner_code='elcomercio')
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
                subject=('[Test]' if settings.ENVIRONMENT == 'test' else '[Production]') + ' No llego notificacion de comprobantes de siebel',
                to_emails=LIST_EMAIL_SENDER,
                from_email=from_email,
                context={
                    'error': str(list_error_message),
                }
            )
        print('Termino la ejecucion del comando')
