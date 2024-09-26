import json
import requests

from sentry_sdk import capture_exception, capture_event
from django.core.management.base import BaseCommand
from apps.paywall.models import Subscription, Operation
from apps.siebel.models import SiebelConfirmationPayment


class Command(BaseCommand):
    help = 'Este comando añade las notificaciones de siebel'
    """
        python3 manage.py update_notification_siebel
    """

    def handle(self, *args, **options):
        confirmations = SiebelConfirmationPayment.objects.filter(operation=None, cip=None)
        for confirmation in confirmations:
            if confirmation.cod_delivery:
                if Subscription.objects.filter(delivery=confirmation.cod_delivery).exists():
                    if confirmation.num_liquidacion == 'VENTA':
                        operation_obj = Operation.objects.filter(
                            payment__subscription__delivery=confirmation.cod_delivery,
                            ope_amount__gte=5
                        ).order_by('created').first()
                        confirmation.operation = operation_obj
                        confirmation.save()
                        print('{} - {}'.format(confirmation.cod_delivery, confirmation.num_liquidacion))
                    else:
                        try:
                            operation_ = Operation.objects.get(
                                payment__payu_transaction=confirmation.num_liquidacion
                            )
                        except Exception as e:
                            print(e)
                            operation_ = None

                        if operation_:
                            confirmation.operation = operation_
                            confirmation.save()
                            print('{} - {}'.format(confirmation.cod_delivery, confirmation.num_liquidacion))

