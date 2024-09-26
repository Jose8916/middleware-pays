import json
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.utils.timezone import get_default_timezone
from rest_framework.views import APIView
from sentry_sdk import capture_exception
from django.db.models import Q

from apps.paywall.models import Subscription
from apps.paywall.utils_dwh import UsersSubscription


class SubscriptionApiView(APIView):

    def start_date(self, date_start):
        start = datetime.combine(
            datetime.strptime(date_start, "%Y-%m-%d"),
            datetime.min.time()
        )
        return get_default_timezone().localize(start)

    def end_date(self, date_end):
        end = datetime.combine(
            datetime.strptime(date_end, "%Y-%m-%d"),
            datetime.max.time()
        )
        return get_default_timezone().localize(end)

    def post(self, request, *args, **kwargs):
        """
        Retorna los datos de las suscripciones para datawarehouse.

        Parámetros:
        - date_start: Fecha de inicio en formato %Y-%m-%d
        - date_end: Fecha de fin en formato %Y-%m-%d
        """
        body = request.body.decode('utf-8')
        received_json_data = json.loads(body)

        date_start = received_json_data.get('date_start', '')
        date_end = received_json_data.get('date_end', '')

        date_range = (self.start_date(date_start), self.end_date(date_end))

        subscription_list = Subscription.objects.filter(
            Q(created__range=date_range) |
            Q(last_updated__range = date_range)
        )

        list_users = []
        for subscription in subscription_list:
            if subscription.by_payu_method():
                try:
                    users_suscription = UsersSubscription(subscription)
                    list_users.append(users_suscription.format_user())
                except Exception:
                    capture_exception()

        return JsonResponse(list_users, safe=False)
