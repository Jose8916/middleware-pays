"""
    Cliente para el envío de suspensiones temporales a Siebel
"""

from urllib.parse import urljoin

from sentry_sdk import capture_exception, capture_event, capture_message
import requests

from ..settings import PAYWALL_SIEBEL_COMISIONES_URL


class SuspensionClient:

    log_class = None
    siebel_url = PAYWALL_SIEBEL_COMISIONES_URL

    def __init__(self, log_class=None, siebel_url=None):

        self.log_class = log_class

        if siebel_url:
            self.siebel_url = siebel_url

    def get_siebel_url(self, endpoint):
        return urljoin(self.siebel_url, endpoint)

    def siebel_suspend(self, siebel_action):
        siebel_subscription = siebel_action.siebel_subscription
        delivery = siebel_subscription.siebel_delivery
        payload = {
            'codDelivery': delivery
        }

        result, status_code = self.siebel_request_get(
            url=self.get_siebel_url('/wsSuscripcionesPaywall/suspender.suscripciones'),
            siebel_action=siebel_action,
            payload=payload
        )

        self.check_result(
            result=result,
            status_code=status_code,
            siebel_subscription=siebel_subscription
        )

    def check_result(self, result, status_code, siebel_subscription):

        if status_code == 200:
            siebel_subscription.status = siebel_subscription.STATUS_SUSPEND
            siebel_subscription.save()

    def siebel_request_get(self, url, payload, siebel_action):
        try:
            response = requests.get(
                url, params=payload
            )
            """
            capture_event(
                {
                    'message': 'siebel_request_get %s' % response.url,
                    'extra': {
                        'url': response.url,
                        'payload': payload,
                        'response': response.text,
                        'request': str(response.request.body),
                        'headers': response.request.headers,
                        'response_code': response.status_code,
                        'siebel_action_id': siebel_action.id,
                    },
                }
            )
            """
            result, http_status_code = response.json(), response.status_code

        except Exception:
            capture_exception()
            result, http_status_code = {}, None

        else:
            siebel_action.register_hit(
                payload=payload,
                result=result,
                http_status_code=http_status_code
            )

            self.save_club_log(
                siebel_action=siebel_action,
                request=response.request,
                response=response,
            )

        return result, http_status_code

    def save_club_log(self, request, response, siebel_action):

        if self.log_class:
            club_log = self.log_class()
            club_log.siebel_action = siebel_action
            club_log.url = response.url
            club_log.request_text = str(request.body)
            club_log.response_text = response.text
            club_log.response_code = response.status_code
            club_log.response_time = response.elapsed.total_seconds()
            club_log.save()
