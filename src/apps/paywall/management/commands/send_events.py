# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from apps.paywall.models import FinancialTransaction, Subscription, Payment
from apps.arcsubs.models import Event
import requests
import json
import pytz
from datetime import datetime, timedelta
from django.conf import settings


class Command(BaseCommand):
    help = 'Envia eventos que no han sido capturados'
    # python3 manage.py send_events --start_subscription 1 # esta incompleto
    # python3 manage.py send_events --terminate_subscription 2
    # python3 manage.py send_events --payments 1

    def add_arguments(self, parser):
        parser.add_argument('--start_subscription', nargs='?', type=str)
        parser.add_argument('--terminate_subscription', nargs='?', type=str)
        parser.add_argument('--payments', nargs='?', type=str)

    def handle(self, *args, **options):
        if options.get('start_subscription'):  # no se uso
            transactions = FinancialTransaction.objects.filter(subscription_obj=None)
            for transaction in transactions.iterator():
                try:
                    subscription = Subscription.objects.filter(arc_id=transaction.subscription_id).exists()
                    if not subscription:
                        url = "https://paywall.comerciosuscripciones.pe/events/api/subscription/start/"

                        payload = {
                            "suscription_id": transaction.subscription_id,
                            "site": transaction.pa,
                            "event": "START_SUBSCRIPTION",
                            "subscription": transaction.subscription_id
                        }
                        headers = {
                            'Content-Type': 'application/json',
                            'Authorization': 'Token 5088cbc5ceb807c702b4e3487173ef792eb50be4',
                            'Arc-Site': 'gestion'
                        }
                        response = requests.post(
                            url,
                            data=json.dumps(payload),
                            headers=headers,
                        )
                        print(response.text.encode('utf8'))
                except Exception as e:
                    subscription = ''

            print('Ejecucion exitosa')
        elif options.get('terminate_subscription'):
            hoursAgo = options.get('terminate_subscription')
            startDate = datetime.now(pytz.timezone('America/Lima')) - timedelta(hours=int(hoursAgo))
            startDate = int(datetime.timestamp(startDate) * 1000)

            endDate = datetime.now(pytz.timezone('America/Lima'))
            endDate = int(datetime.timestamp(endDate) * 1000)

            terminations = Event.objects.filter(
                event_type='TERMINATE_SUBSCRIPTION',
                timestamp__range=(startDate, endDate)
            )

            for event_termination in terminations.iterator():
                message = event_termination.message

                if not Subscription.objects.filter(arc_id=message['subscriptionID'], state=2).exists():
                    if settings.ENVIRONMENT == 'production':
                        url = "https://paywall.comerciosuscripciones.pe/events/api/subscription/fail_renew/"
                        token = 'Token 5088cbc5ceb807c702b4e3487173ef792eb50be4'
                    elif settings.ENVIRONMENT == 'test':
                        url = "http://devpaywall.comerciosuscripciones.pe/events/api/subscription/fail_renew/"
                        token = 'Token deb904a03a4e31d420a014534514b8cc8ca4d111'

                    if url:
                        payload = {
                            "subscription": message['subscriptionID'],
                            "site": event_termination.site,
                            "event": "TERMINATE_SUBSCRIPTION",
                            "event_index": event_termination.timestamp
                        }
                        headers = {
                            'Content-Type': 'application/json',
                            'Authorization': token
                        }
                        response = requests.post(
                            url,
                            data=json.dumps(payload),
                            headers=headers,
                        )
                        print(response.text.encode('utf8'))
                        print(message['subscriptionID'])
        elif options.get('payments'):
            transactions = FinancialTransaction.objects.filter(
                transaction_type='Payment',
                payment=None
            )
            for transaction in transactions.iterator():
                try:
                    if not Payment.objects.filter(arc_order=transaction.order_number).exists():
                        if settings.ENVIRONMENT == 'production':
                            url = "https://paywall.comerciosuscripciones.pe/events/api/subscription/renew/"
                            token = 'Token 5088cbc5ceb807c702b4e3487173ef792eb50be4'
                        elif settings.ENVIRONMENT == 'test':
                            url = "http://devpaywall.comerciosuscripciones.pe/events/api/subscription/renew/"
                            token = 'Token deb904a03a4e31d420a014534514b8cc8ca4d111'

                        if transaction.site == '1':
                            site == 'gestion'
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
                            response = requests.post(
                                url,
                                data=json.dumps(payload),
                                headers=headers,
                            )
                            print(response.text.encode('utf8'))
                            print(transaction.subscription_id)
                except Exception as e:
                    print(e)
                    pass

            print('Ejecucion exitosa')