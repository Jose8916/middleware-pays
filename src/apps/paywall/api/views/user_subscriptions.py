import json

from datetime import datetime
from django.http import JsonResponse
from django.utils.timezone import get_default_timezone
from rest_framework.views import APIView

from apps.paywall.models import Operation
from apps.paywall.utils_report_subscription import UsersSubscription
from django.db.models import Q


class UserSubscriptionApiView(APIView):

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
        items_page = 1500

        date_start = received_json_data.get('date_start', '')
        date_end = received_json_data.get('date_end', '')

        # subscription_list = Subscription.objects.filter(
        #     plan__arc_pricecode='GLK0AJ',
        #     payment_profile__isnull=False,
        #     created__range=(
        #         self.start_date(date_start),
        #         self.end_date(date_end)
        #     )
        # )
        #
        operation_list = Operation.objects.filter(
            payment_profile__isnull=False,
            payment__date_payment__range=(self.start_date(date_start), self.end_date(date_end))
        )

        if page:
            page = int(page)
            end_item = page * items_page
            if page == 1:
                start_item = 0
            else:
                start_item = (page - 1) * items_page
            operation_list = operation_list[start_item:end_item]

        list_users = []

        # for subscription in subscription_list:
        #     user_suscription_free = UsersSubscriptionFree(subscription)
        #     list_users.append(user_suscription_free.format_user())

        for operation in operation_list:
            users_suscription = UsersSubscription(operation)
            list_users.append(users_suscription.format_user())

        return JsonResponse(list_users, safe=False)
