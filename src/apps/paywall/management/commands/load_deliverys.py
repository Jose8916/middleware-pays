import json
import requests

from sentry_sdk import capture_exception, capture_event
from django.core.management.base import BaseCommand
from apps.paywall.models import Subscription, Operation


class Command(BaseCommand):
    help = 'Este comando carga el historial de deliverys'
    """
        python3 manage.py load_deliverys
    """

    def get_siebel_delivery(self, subscription):
        try:
            obj_operation = Operation.objects.get(payment__subscription=subscription,
                                                  siebel_delivery__isnull=False)
            if obj_operation:
                return obj_operation.siebel_delivery
            else:
                return ''
        except Operation.DoesNotExist:
            # no existe operacion
            return ''
        except Exception as e:
            print(e)
            print(subscription.arc_id)
            capture_event(
                {
                    'message': 'error en carga de delivery',
                    'extra': {
                        'suscripcion': subscription.arc_id,
                        'error': e,
                    },
                }
            )
            return ''

    def handle(self, *args, **options):
        subscriptions = Subscription.objects.filter(delivery=None)
        for subscription in subscriptions:
            if self.get_siebel_delivery(subscription):
                print(self.get_siebel_delivery(subscription))
                subscription.delivery = self.get_siebel_delivery(subscription)
                subscription.save()
