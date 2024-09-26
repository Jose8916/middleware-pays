import json

from datetime import datetime
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.utils.timezone import get_default_timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.paywall.models import Subscription
from apps.paywall.utils_subscription_free_comercio import UsersSubscriptionFree


class FreeSubscriptionApiView(APIView):
    permission_classes = (AllowAny,)
    items_page = 2000

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
        page = received_json_data.get('page', '')

        date_start = received_json_data.get('date_start', '')
        date_end = received_json_data.get('date_end', '')

        subscription_list = Subscription.objects.filter(
            Q(last_updated__range=(self.start_date(date_start), self.end_date(date_end))) |
            Q(created__range=(self.start_date(date_start), self.end_date(date_end))),
            plan__product__arc_sku=settings.SUBSCRIPTION_7_DAYS_SKU,
            plan__arc_pricecode=settings.SUBSCRIPTION_7_DAYS_PRICECODE,
        )

        if page:
            page = int(page)
            end_item = page * self.items_page
            if page == 1:
                start_item = 0
            else:
                start_item = (page - 1) * self.items_page
            subscription_list = subscription_list[start_item:end_item]

        list_users = []

        for subscription in subscription_list:
            user_suscription_free = UsersSubscriptionFree(subscription)
            list_users.append(user_suscription_free.format_user())
        return JsonResponse(list_users, safe=False)
