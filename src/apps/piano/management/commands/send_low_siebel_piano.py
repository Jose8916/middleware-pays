from django.core.management.base import BaseCommand
from apps.piano.models import LowSubscriptions, Unsubscribe, Transaction
from apps.siebel.models import LogUnsubscribePiano
from apps.siebel.siebel_clients import SiebelClient
from apps.paywall.models import Subscription as ArcSubscription, Operation
from django.utils import timezone


class Command(BaseCommand):
    help = 'Crea las ordenes de venta de siebel'
    """
        Uso normal: python3 manage.py send_low_siebel
        Modo test: python3 manage.py send_low_siebel_piano --test_mode 1
        Envio de un nro n de elementos: python3 manage.py send_low_siebel_piano --filter_elements 2 
    """

    def add_arguments(self, parser):
        parser.add_argument('--test_mode', nargs='?', type=str)
        parser.add_argument('--filter_elements', nargs='?', type=str)

    def handle(self, *args, **options):
        tz = timezone.get_current_timezone()
        test_mode = True if options.get('test_mode', '') == '1' else False

        subscription_list = LowSubscriptions.objects.filter(
            subscription__delivery__isnull=False,
        ).exclude(unsubscribe__sent_to_siebel=True).exclude(exclude_to_send_siebel=True)
        
        if options.get('filter_elements', ''):
            subscription_list = subscription_list[:int(options.get('filter_elements'))]

        for subscription_obj in subscription_list:
            if not Transaction.objects.filter(subscription=subscription_obj.subscription).exists():
                trans_obj = 1
            else:
                trans_obj = Transaction.objects.filter(
                    siebel_payment__cod_response=True,
                    subscription=subscription_obj.subscription
                ).order_by('access_from_date').last()

            if trans_obj and subscription_obj.subscription.delivery:
                delivery = subscription_obj.subscription.delivery
                if ArcSubscription.objects.filter(delivery=delivery).exists():
                    valid_operation = Operation.objects.filter(
                        conciliation_cod_response='1',
                        payment__subscription__delivery=delivery
                    ).order_by('payment__date_payment').last()
                    if valid_operation:
                        pass
                    else:
                        continue

                date_low = subscription_obj.low_subscription
                date_unsubscribe = date_low.astimezone(tz)
                request_siebel, response = SiebelClient().unsubscribe(delivery, date_unsubscribe, test_mode)
                if response:
                    try:
                        submitted_successfully = int(response.get('response', {}).get('respuesta', ''))
                    except:
                        submitted_successfully = ''

                    if subscription_obj.unsubscribe:
                        unsubs = subscription_obj.unsubscribe
                        unsubs.siebel_request = request_siebel
                        unsubs.siebel_response = response
                        unsubs.sent_to_siebel = True if submitted_successfully == 1 else False
                        unsubs.save()
                    else:
                        instance = Unsubscribe(
                            siebel_request=request_siebel,
                            siebel_response=response,
                            sent_to_siebel=True if submitted_successfully == 1 else False
                        )
                        instance.save()
                        subscription_obj.unsubscribe = instance
                        subscription_obj.save()

                    log_unsubscribe = LogUnsubscribePiano(
                        siebel_request=request_siebel,
                        siebel_response=response,
                        sent_to_siebel=True if submitted_successfully == 1 else False,
                        subscription_low=subscription_obj
                    )
                    log_unsubscribe.save()

        print('Termino la ejecucion del comando')
