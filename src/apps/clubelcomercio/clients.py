from urllib.parse import urljoin

from sentry_sdk import capture_exception, capture_event, capture_message
import requests
from django.utils import timezone
# from .models import ClubRegister
from apps.piano.models import Subscription as SubscriptionPiano
from .utils import date_start_subscription
from .settings import PAYWALL_CLUB_URL, PAYWALL_CLUB_TOKEN


class ClubClient:
    log_class = None
    club_url = PAYWALL_CLUB_URL
    club_token = PAYWALL_CLUB_TOKEN

    def __init__(self, log_class=None, club_url=None, club_key=None, club_token=None):

        self.log_class = log_class

        if club_url:
            self.club_url = club_url

        if club_token:
            self.club_token = club_token

    def integration_activate(self, club_integration):
        club_subscription = club_integration.club_subscription

        result, _ = self.club_send_post(
            url=self.get_club_url('/services/subscription-online/register'),
            payload=self.get_activate_payload(club_integration=club_integration),
            club_integration=club_integration
        )

        if result.get('status') == 200:
            club_subscription.club_activated = timezone.now()
            club_subscription.is_active = True
            club_subscription.club_is_new = result.get('is_new')
            club_subscription.club_credentials = result.get('create_credentials')
            club_subscription.save()
        else:
            capture_event(
                {
                    'message': 'error en el envio a club',
                    'extra': {
                        'arc_order': result.get('status', ''),
                    },
                }
            )

    def register_club(self, body, club):
        result, _ = self.club_send_piano_post(
            url=self.get_club_url('/services/subscription-online/register'),
            payload=body
        )

        try:
            club.subscription_str = body.get('ope_id_piano')
            club.email = body.get('email')
            club.send = True
            club.request_json = body
            club.response_json = result
            club.status_response = result.get('status')
            club.is_new = result.get('is_new')
            club.create_credentials = result.get('create_credentials')
            club.valid = result.get('valid')

            club.save()
            if result.get('status') == 200:
                obj_subscription = SubscriptionPiano.objects.get(subscription_id=body.get('ope_id_piano'))
                obj_subscription.sent_club = True
                obj_subscription.save()
                return True, 'Exito'
            else:
                return False, str(result)
        except Exception as e:
            capture_exception()
            return False, str(e)

    def integration_deactivate(self, club_integration):
        club_subscription = club_integration.club_subscription

        result, _ = self.club_send_post(
            url=self.get_club_url('/services/subscription-online/annulled'),
            payload=self.get_deactivate_payload(club_integration=club_integration),
            club_integration=club_integration
        )

        if result.get('status') == 200:
            club_subscription.club_deactivated = timezone.now()
            club_subscription.is_active = False
            club_subscription.save()

    def integration_update(self, club_integration):
        club_subscription = club_integration.club_subscription

        result, _ = self.club_send_post(
            url=self.get_club_url('/services/subscription-online/update-data-subscriber'),
            payload=self.get_update_payload(club_integration=club_integration),
            club_integration=club_integration
        )

        if result.get('status') == 200:
            club_subscription.club_updated = timezone.now()
            club_subscription.save()

    def get_club_url(self, endpoint):
        return urljoin(PAYWALL_CLUB_URL, endpoint)

    def get_club_headers(self):
        return {
            "content-type": "application/json",
            "token": PAYWALL_CLUB_TOKEN,
        }

    def get_activate_payload(self, club_integration):
        club_subscription = club_integration.club_subscription
        subscription = club_subscription.subscription
        profile = subscription.payment_profile
        portal = subscription.partner
        return {
            "name": profile.prof_name,
            "mother_sure_name": profile.prof_lastname_mother,
            "last_name": profile.prof_lastname,
            "document_type": club_subscription.document_type,
            "document_number": club_subscription.document_number,
            "email": club_subscription.email,
            "product_code": "",
            "package_code": "",
            "date_initial": date_start_subscription(subscription),
            "date_end": None,
            "ope_id": club_subscription.club_operation,
            "gender": None,
            "birthdate": None,
            "telephone": profile.prof_phone or "",
            "state_recurrent": 1,
            "program": portal.partner_code,
            "origin": "paywall",
        }

    def get_deactivate_payload(self, club_integration):
        club_subscription = club_integration.club_subscription
        subscription = club_subscription.subscription
        return {
            "ope_id": club_subscription.club_operation,
            "origin": "paywall",
        }

    def get_update_payload(self, club_integration):
        club_subscription = club_integration.club_subscription
        subscription = club_subscription.subscription
        profile = subscription.payment_profile
        return {
            "name": profile.prof_name,
            "mother_sure_name": profile.prof_lastname_mother,
            "last_name": profile.prof_lastname,
            "document_type": club_subscription.document_type,
            "document_number": club_subscription.document_number,
            "email": club_subscription.email,
            "ope_id": club_subscription.club_operation,
            "origin": "paywall",
        }

    def save_club_log(self, request, payload, response, club_integration):

        if self.log_class:
            club_log = self.log_class()
            club_log.club_integration = club_integration
            club_log.url = response.url
            club_log.request_json = payload
            club_log.request_text = str(request.body)
            club_log.response_text = response.text
            club_log.response_code = response.status_code
            club_log.response_time = response.elapsed.total_seconds()
            club_log.save()

    def club_send_post(self, url, payload, club_integration):

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.get_club_headers()
            )
            result, http_status_code = response.json(), response.status_code

        except Exception:
            capture_exception()
            result, http_status_code = {}, None

        else:
            club_integration.register_hit(
                payload=payload,
                result=result,
                http_status_code=http_status_code
            )

            self.save_club_log(
                club_integration=club_integration,
                payload=payload,
                request=response.request,
                response=response,
            )

        return result, http_status_code

    def club_send_piano_post(self, url, payload):

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.get_club_headers()
            )
            result, http_status_code = response.json(), response.status_code

        except Exception:
            capture_exception()
            result, http_status_code = {}, None

        return result, http_status_code
