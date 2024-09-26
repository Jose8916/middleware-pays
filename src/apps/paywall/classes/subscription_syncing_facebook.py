from django.conf import settings
from apps.paywall.models import Subscription, SubscriptionState, Partner, SubscriptionFIA
from apps.arcsubs.utils import timestamp_to_datetime
from apps.paywall.utils import current_time
from sentry_sdk import capture_message, capture_exception, capture_event
from django.core.mail import EmailMessage

import requests


class SubscriptionSyncingFacebook(object):
    DOMAIN_GRAPH_FACEBOOK = 'https://graph.facebook.com'
    VERSION_GRAPH_FACEBOOK = 'v2.10'

    def __init__(self, subscription, site):
        self.subscription = subscription
        self.site = site

    def get_state_subscription(self, subscription):
        if subscription.state in (Subscription.ARC_STATE_ACTIVE, Subscription.ARC_STATE_CANCELED,
                                  Subscription.ARC_STATE_SUSPENDED):
            return True
        else:
            return False

    def get_final_payment(self, subscription):
        final_payment = subscription.data.get('paymentHistory')[-1]
        return final_payment.get('periodTo')

    def get_date_to_expire(self):
        return current_time().strftime("%Y-%m-%dT%H:%M:%S")

    def update_data(self):
        if self.subscription.data:
            try:
                number_subscription = Subscription.objects.filter(
                    arc_user__uuid=self.subscription.arc_user.uuid,
                    partner__partner_code=self.site
                ).exclude(
                    state=Subscription.ARC_STATE_TERMINATED
                ).count()

                if not number_subscription:
                    state_subscription = self.get_state_subscription(self.subscription)
                    data = {
                        "subscriptions": [{
                            "publisher_user_id": str(self.subscription.arc_user.uuid),
                            "is_active": state_subscription,
                            "expiry_time": self.get_date_to_expire() + "+00:00"
                        }]
                    }

                    headers = {'content-type': 'application/json'}

                    # sending post request and saving response as response object
                    end_point = '/{version_graph_facebook}/{subscription_node}/subscriptions?access_token={access_token}'\
                        .format(version_graph_facebook=self.VERSION_GRAPH_FACEBOOK,
                                subscription_node=self.subscription.partner.subscription_node_id_facebook,
                                access_token=self.subscription.partner.access_token_facebook)
                    r = requests.post(url=self.DOMAIN_GRAPH_FACEBOOK + end_point,
                                      json=data,
                                      headers=headers)
                    if r.status_code != 200:
                        state_syncing = SubscriptionFIA.SYNCING_FIA_ERROR
                        capture_event(
                            {
                                'message': 'error in syncing_face',
                                'extra': {
                                    'response': r.json(),
                                    'uuid': str(self.subscription.arc_user.uuid),
                                    'data': data,
                                }
                            }
                        )
                    else:
                        state_syncing = SubscriptionFIA.SYNCING_FIA_SUCCESS
                        capture_event(
                            {
                                'message': 'Exito syncingface',
                                'extra': {
                                    'data_enviada': data,
                                    'response': r.json()
                                }
                            }
                        )

                    brand = Partner.objects.get(partner_code=self.site)
                    subs_fia = SubscriptionFIA(
                        subscription=self.subscription,
                        fia_request=data,
                        fia_response=r.json(),
                        state=state_syncing,
                        partner=brand
                    )
                    subs_fia.save()
            except Exception:
                capture_exception()
            except SystemExit:
                capture_exception()
