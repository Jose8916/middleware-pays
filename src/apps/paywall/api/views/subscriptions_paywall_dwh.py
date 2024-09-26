from datetime import datetime, timedelta
import json

from django.db.models import Q
from django.http import JsonResponse
from rest_framework import status
from django.utils.timezone import get_default_timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from sentry_sdk import capture_exception

from apps.paywall.models import Subscription
from apps.paywall.utils_dwh import UsersSubscription


class SubscriptionUniqueApiView(APIView):

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

    def get_date_range(self, request):
        body = request.body.decode('utf-8')
        received_json_data = json.loads(body)
        date_start = received_json_data.get('date_start', '')
        date_end = received_json_data.get('date_end', '')

        return (
            self.start_date(date_start),
            self.end_date(date_end)
        )

    def post(self, request, *args, **kwargs):
        """
        Retorna los datos de las suscripciones para datawarehouse.

        Parámetros:
        - date_start: Fecha de inicio en formato %Y-%m-%d
        - date_end: Fecha de fin en formato %Y-%m-%d
        """
        page = request.GET.get('page', '')
        date_range = self.get_date_range(request=request)
        items_page = 100

        subscription_list = Subscription.objects.filter(
            starts_date__range=date_range
        )

        if page:
            page = int(page)
            end_item = page * items_page
            if page == 1:
                start_item = 0
            else:
                start_item = (page - 1) * items_page
            subscription_list = subscription_list[start_item:end_item]

        list_users = []

        for subscription in subscription_list:
            try:
                payu_method = subscription.by_payu_method()

            except Exception:
                capture_exception()
                payu_method = ''

            except SystemExit:
                capture_exception()
                payu_method = ''

            if payu_method:
                try:
                    users_suscription = UsersSubscription(subscription)
                    list_users.append(users_suscription.format_user())
                except Exception:
                    capture_exception()

                except SystemExit:
                    capture_exception()

        return Response(
            list_users,
            status=status.HTTP_200_OK
        )
