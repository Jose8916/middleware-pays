import json
import requests

from sentry_sdk import capture_exception, capture_event
from django.core.management.base import BaseCommand
from apps.paywall.models import Subscription, Operation
from apps.siebel.models import SiebelConfirmationPayment


class Command(BaseCommand):
    help = 'Este comando elimina las notificaciones de siebel'
    """
        python3 manage.py delete_notification_siebel
    """

    def handle(self, *args, **options):
        confirmations = SiebelConfirmationPayment.objects.filter(operation=None)
        for confirmation in confirmations:
            if not Subscription.objects.filter(delivery=confirmation.cod_delivery).exists():
                print(confirmation.cod_delivery)
                confirmation.delete()
