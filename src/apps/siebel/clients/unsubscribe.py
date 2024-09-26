"""
    Cliente para el envío de anulaciones a Siebel
"""

from urllib.parse import urljoin
from django.utils import formats, timezone
from sentry_sdk import capture_exception, capture_event, capture_message
import requests
from apps.siebel.models import ArcUnsubscribe, LogArcUnsubscribe
from apps.siebel.siebel_clients import SiebelClient
from django.conf import settings


class UnsubscribeClient:

    def siebel_suspend(self, subscription, test_mode):

        tz = timezone.get_current_timezone()
        date_unsubscribe = subscription.date_anulled.astimezone(tz)
        request_siebel, response = SiebelClient().unsubscribe(subscription.delivery, date_unsubscribe, test_mode)
        if response:
            try:
                submitted_successfully = int(response.get('response', {}).get('respuesta', ''))
            except:
                submitted_successfully = ''

            if ArcUnsubscribe.objects.filter(subscription=subscription).exists():
                arc_unsubscribe = ArcUnsubscribe.objects.get(subscription=subscription)
                arc_unsubscribe.siebel_request = request_siebel
                arc_unsubscribe.siebel_response = response
                arc_unsubscribe.sent_to_siebel = True if submitted_successfully == 1 else False
                arc_unsubscribe.save
            else:
                instance = ArcUnsubscribe(
                    siebel_request=request_siebel,
                    siebel_response=response,
                    sent_to_siebel=True if submitted_successfully == 1 else False,
                    subscription=subscription
                )
                instance.save()

            log_unsubscribe = LogArcUnsubscribe(
                siebel_request=request_siebel,
                siebel_response=response,
                sent_to_siebel=True if submitted_successfully == 1 else False,
                subscription=subscription
            )
            log_unsubscribe.save()
