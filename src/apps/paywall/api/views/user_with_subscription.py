import json

from datetime import datetime
from django.http import JsonResponse
from django.utils.timezone import get_default_timezone
from rest_framework.views import APIView

from apps.paywall.models import Subscription
from apps.paywall.utils_report_subscription import UsersSubscription
from django.db.models import Q


class UserWithSubscriptionApiView(APIView):

    def post(self, request, *args, **kwargs):
        """
        Retorna los datos de las suscripciones para datawarehouse.

        Parámetros:
        - date_start: Fecha de inicio en formato %Y-%m-%d
        - date_end: Fecha de fin en formato %Y-%m-%d
        """

        body = request.body.decode('utf-8')
        received_json_data = json.loads(body)
        uuid = received_json_data.get('uuid', '')

        try:
            subscription = Subscription.objects.filter(
                arc_user__uuid=uuid
            ).exists()
            response_value = {
                "value": subscription
            }
        except Exception as e:
            response_value = {
                "value": False
            }

        return JsonResponse(response_value, safe=False)
