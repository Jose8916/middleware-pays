import json
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.utils.timezone import get_default_timezone
from rest_framework.views import APIView
from sentry_sdk import capture_exception
from django.db.models import Q

from apps.paywall.models import Subscription, Plan
from apps.paywall.utils_dwh import UsersSubscription


class SubscriptionStateView(APIView):

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

        list_plan=[]
        plans = Plan.objects.filter(state=True)
        for plan in plans:
            if plan.arc_pricecode:
                try:
                    marca = plan.partner.partner_name
                except:
                    marca = ''

                list_plan.append(
                    {
                        'name': plan.plan_name + ' - ' + marca,
                        'arc_pricecode': plan.arc_pricecode
                    }
                )

        new_subscription_list = Subscription.objects.filter(
            starts_date__range=date_range
        )

        terminate_subscription_list = Subscription.objects.filter(
            date_anulled__range=date_range
        )

        suscription_row = []

        for plan_l in list_plan:
            suscription_high = new_subscription_list.filter(plan__arc_pricecode=plan_l.get('arc_pricecode'))
            suscription_low = terminate_subscription_list.filter(plan__arc_pricecode=plan_l.get('arc_pricecode'))

            suscription_row.append(
                {
                    'nombre': plan_l.get('name'),
                    'suscription_alta': suscription_high.count(),
                    'suscription_baja': suscription_low.count()
                }
            )

        return JsonResponse(suscription_row, safe=False)
