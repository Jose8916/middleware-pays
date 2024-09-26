import json

from datetime import datetime
from django.http import JsonResponse
from django.utils.timezone import get_default_timezone
from django.db.models import Q

from rest_framework.views import APIView

from apps.paywall.models import Collaborators
from apps.paywall.utils_collaborator import Collaborator


class CollaboratorsApiView(APIView):

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

        collaborators_list = Collaborators.objects.filter(
            Q(last_updated__range=(self.start_date(date_start), self.end_date(date_end))) |
            Q(created__range=(self.start_date(date_start), self.end_date(date_end))),
        ).exclude(data__subscriptionID__isnull=True).exclude(data__subscriptionID__exact='')
        print(collaborators_list.query)

        list_users = []
        for collaborator in collaborators_list:
            users_suscription = Collaborator(collaborator)
            list_users.append(users_suscription.format_user())

        return JsonResponse(list_users, safe=False)
