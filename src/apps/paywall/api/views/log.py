from rest_framework import status
from rest_framework.permissions import AllowAny
from django.http import HttpResponse
from rest_framework.views import APIView

from ...models import Log


class LogAPIView(APIView):
    permission_classes = (AllowAny, )

    def get(self, request, *args, **kwargs):
        """
                Genera el token para consultar si un DNI es suscriptor.

                HTTP headers:
                - user-token: 'access_token' de ARC
                - Arc-Site: Site de ARC (gestion | elcomercio)
                """

        # validate User - Token Access
        data = request.data
        """
        body = request.body.decode('utf-8')
        received_json_data = json.loads(body)
        date_start = received_json_data.get('date_start', '')
        """

        b = Log(text_log=data['text_log'])
        b.save()
        return HttpResponse('Exito')

    def post(self, request):
        """
        Genera el token para consultar si un DNI es suscriptor.

        HTTP headers:
        - user-token: 'access_token' de ARC
        - Arc-Site: Site de ARC (gestion | elcomercio)
        """

        # validate User - Token Access
        data = request.data
        """
        body = request.body.decode('utf-8')
        received_json_data = json.loads(body)
        date_start = received_json_data.get('date_start', '')
        """

        b = Log(text_log=data['text_log'])
        b.save()
        return HttpResponse('Exito')
