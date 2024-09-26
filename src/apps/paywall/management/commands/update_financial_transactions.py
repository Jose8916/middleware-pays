# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from apps.paywall.models import FinancialTransaction, Subscription, Payment, Operation, EventReport
from django.conf import settings
from apps.paywall.arc_clients import SalesClient
import requests
import json


class Command(BaseCommand):
    help = 'Relaciona las suscripciones y pagos a la tabla FinancialTransaction'
    # python3 manage.py update_financial_transactions --subscriptions 1
    # python3 manage.py update_financial_transactions --payments 1
    # python3 manage.py update_financial_transactions --verifySubscriptions 1
    # python3 manage.py update_financial_transactions --terminations 1

    def add_arguments(self, parser):
        parser.add_argument('--subscriptions', nargs='?', type=str)
        parser.add_argument('--payments', nargs='?', type=str)
        parser.add_argument('--verifySubscriptions', nargs='?', type=str)
        parser.add_argument('--terminations', nargs='?', type=str)

    def send_events_missing_payments(self):
        f_transactions = FinancialTransaction.objects.filter(
            payment=None,
            transaction_type='Payment',
            initial_transaction='False'
        )

        for transaction in f_transactions.iterator():
            try:
                if not Payment.objects.filter(arc_order=transaction.order_number).exists():
                    if settings.ENVIRONMENT == 'production':
                        url = "https://paywall.comerciosuscripciones.pe/events/api/subscription/renew/"
                        token = 'Token 5088cbc5ceb807c702b4e3487173ef792eb50be4'
                    elif settings.ENVIRONMENT == 'test':
                        url = "http://devpaywall.comerciosuscripciones.pe/events/api/subscription/renew/"
                        token = 'Token deb904a03a4e31d420a014534514b8cc8ca4d111'

                    if transaction.site == '1':
                        site = 'gestion'
                    elif transaction.site == '2':
                        site = 'elcomercio'
                    else:
                        site = ''

                    if site:
                        payload = {
                            "suscription_id": transaction.subscription_id,
                            "site": site,
                            "event": "RENEW_SUBSCRIPTION",
                            "subscription": transaction.subscription_id
                        }
                        headers = {
                            'Content-Type': 'application/json',
                            'Authorization': token,
                            'Arc-Site': site
                        }
                        print('************')
                        response = requests.post(
                            url,
                            data=json.dumps(payload),
                            headers=headers,
                        )

                        print(response.text.encode('utf8'))
                        print('enviado payment' + str(transaction.subscription_id))
                        print('************')
            except Exception as e:
                print(e)
                pass

    def send_events_missing_subscriptions(self):
        f_transactions = FinancialTransaction.objects.filter(
            subscription_obj=None,
            transaction_type='Payment',
            initial_transaction='True'
        )

        for transaction in f_transactions.iterator():
            site_name = ''

            if not Payment.objects.filter(arc_order=transaction.order_number).exists():
                if settings.ENVIRONMENT == 'production':
                    url = "https://paywall.comerciosuscripciones.pe/events/api/subscription/start/"
                    token = 'Token 5088cbc5ceb807c702b4e3487173ef792eb50be4'
                elif settings.ENVIRONMENT == 'test':
                    url = "http://devpaywall.comerciosuscripciones.pe/events/api/subscription/start/"
                    token = 'Token deb904a03a4e31d420a014534514b8cc8ca4d111'

                if str(transaction.site) == '1':
                    site_name = 'gestion'
                elif str(transaction.site) == '2':
                    site_name = 'elcomercio'

                if site_name:
                    payload = {
                        "suscription_id": transaction.subscription_id,
                        "site": site_name,
                        "event": "START_SUBSCRIPTION",
                        "subscription": transaction.subscription_id
                    }

                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': token,
                        'Arc-Site': site_name
                    }
                    print('----------------------')

                    response = requests.post(
                        url,
                        data=json.dumps(payload),
                        headers=headers,
                    )

                    print(response.text.encode('utf8'))
                    print('enviado' + str(transaction.subscription_id))
                    print('----------------------')

    def send_events_missing_subscriptions_free(self):
        event_reports = EventReport.objects.filter(
            subscription_obj=None,
            event_type='Start'
        )

        for event in event_reports.iterator():
            if settings.ENVIRONMENT == 'production':
                url = "https://paywall.comerciosuscripciones.pe/events/api/subscription/start/"
                token = 'Token 5088cbc5ceb807c702b4e3487173ef792eb50be4'
            elif settings.ENVIRONMENT == 'test':
                url = "http://devpaywall.comerciosuscripciones.pe/events/api/subscription/start/"
                token = 'Token deb904a03a4e31d420a014534514b8cc8ca4d111'

            payload = {
                "suscription_id": event.subscription_id,
                "site": event.site,
                "event": "START_SUBSCRIPTION",
                "subscription": event.subscription_id
            }

            headers = {
                'Content-Type': 'application/json',
                'Authorization': token,
                'Arc-Site': event.site
            }
            response = requests.post(
                url,
                data=json.dumps(payload),
                headers=headers,
            )
            print('----------------------')
            print(response.text.encode('utf8'))
            print('enviado' + str(event.subscription_id))
            print('----------------------')

    def relates_payments_to_financial_transactions(self):
        transactions = FinancialTransaction.objects.filter(
            payment=None,
            transaction_type='Payment',
            initial_transaction='False'
        )
        for transaction in transactions.iterator():
            try:
                payment = Payment.objects.get(arc_order=transaction.order_number)
            except Payment.DoesNotExist:
                payment = ''
                pass
            except Exception as e:
                payment = ''
                pass

            if payment:
                print('payment {}'.format(payment.subscription.arc_id))
                transaction.payment = payment
                transaction.save()
            operation = ''
            payment = ''

        transactions_op = FinancialTransaction.objects.filter(
            operation=None,
            transaction_type='Payment'
        )
        for transaction_op in transactions_op.iterator():
            try:
                operation = Operation.objects.get(payment__arc_order=transaction_op.order_number)
            except Operation.DoesNotExist:
                operation = ''
                pass
            except Exception as e:
                operation = ''
                pass

            if operation:
                print('operation {}'.format(operation))
                transaction_op.operation = operation
                transaction_op.save()
            operation = ''
            payment = ''

    def handle(self, *args, **options):
        if options.get('subscriptions'):
            transactions = FinancialTransaction.objects.filter(
                subscription_obj=None,
                transaction_type='Payment',
                initial_transaction='True'
            )
            for transaction in transactions.iterator():
                try:
                    subscription = Subscription.objects.get(arc_id=transaction.subscription_id)
                except Exception as e:
                    subscription = ''

                if subscription:
                    print(str(subscription.arc_id) + ' - inicio')
                    transaction.subscription_obj = subscription
                    transaction.save()
                subscription = ''
            self.send_events_missing_subscriptions()

            event_reports = EventReport.objects.filter(
                subscription_obj=None
            )
            for event in event_reports:
                try:
                    subscription = Subscription.objects.get(arc_id=event.subscription_id)
                except Exception as e:
                    subscription = ''
                if subscription:
                    print(str(subscription.arc_id) + ' - event_report')
                    event.subscription_obj = subscription
                    event.save()
            self.send_events_missing_subscriptions_free()
            print('Ejecucion exitosa')

        elif options.get('payments'):
            # relaciona los pagos faltantes en financial transactions
            self.relates_payments_to_financial_transactions()

            # envia eventos de pago faltantes
            self.send_events_missing_payments()
            print('Ejecucion exitosa')

        elif options.get('terminations'):
            subscriptions = Subscription.objects.filter(
                data__currentPaymentMethod__paymentPartner__contains="PayULATAM"
            ).exclude(
                state=Subscription.ARC_STATE_TERMINATED
            )
            for subscription in subscriptions.iterator():
                data_subscription = SalesClient().get_subscription(
                    site=subscription.partner.partner_code,
                    subscription_id=subscription.arc_id
                )
                if data_subscription.get('status') == Subscription.ARC_STATE_TERMINATED:
                    #  envia evento terminado
                    if settings.ENVIRONMENT == 'production':
                        url = "https://paywall.comerciosuscripciones.pe/events/api/subscription/start/"
                        token = 'Token 5088cbc5ceb807c702b4e3487173ef792eb50be4'
                    elif settings.ENVIRONMENT == 'test':
                        url = "http://devpaywall.comerciosuscripciones.pe/events/api/subscription/start/"
                        token = 'Token deb904a03a4e31d420a014534514b8cc8ca4d111'

                    payload = {
                        "suscription_id": subscription.arc_id,
                        "site": subscription.partner.partner_code,
                        "event": "TERMINATE_SUBSCRIPTION",
                        "subscription": subscription.arc_id
                    }
                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': token,
                        'Arc-Site': subscription.partner.partner_code
                    }
                    print('----------------------')
                    print(subscription.arc_id)
                    response = requests.post(
                        url,
                        data=json.dumps(payload),
                        headers=headers,
                    )
                    print(response.text.encode('utf8'))
                    print('----------------------')

        elif options.get('verifySubscriptions'):
            count_different = 0
            count_iguales = 0
            count_raros = 0

            transactions = FinancialTransaction.objects.exclude(subscription_obj=None)
            total = transactions.count()
            for transaction in transactions.iterator():
                try:
                    if int(transaction.subscription_id) != transaction.subscription_obj.arc_id:
                        count_different = count_different + 1
                    elif int(transaction.subscription_id) == transaction.subscription_obj.arc_id:
                        count_iguales = count_iguales + 1
                    else:
                        count_raros = count_raros + 1
                except Exception as e:
                    print(e)
                    pass

            print('hay ' + str(count_different) + 'diferentes')
            print('total de suscripciones' + str(total))
            print('total de iguales' + str(count_iguales))
            print('total de raros' + str(count_raros))


