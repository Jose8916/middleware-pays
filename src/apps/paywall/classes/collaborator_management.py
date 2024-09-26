from apps.paywall.models import Collaborators
from apps.arcsubs.utils import timestamp_to_datetime
from sentry_sdk import capture_exception
from django.db.models import Q


class CollaboratorManagement(object):

    def link_subscription(self, subscription):
        try:
            Collaborators.objects.filter(Q(subscription=0) | Q(subscription=None)).filter(
                subscription_arc=subscription.arc_id
            ).update(subscription=subscription)
        except:
            capture_exception()
