from django.http import JsonResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.paywall.models import Domain
from apps.paywall.paywall_utils import get_arc_user_by_token


class UniversitiesApiView(APIView):
    permission_classes = (AllowAny,)

    def get_celular(self, received_json_data):
        if received_json_data.get('telefono', ''):
            telefono = received_json_data.get('telefono', '')

        elif received_json_data.get('asunto', ''):
            telefono = received_json_data.get('asunto', '')

        else:
            telefono = ''

        return telefono

    def get(self, request, *args, **kwargs):
        """

        """

        # data_response = {
        #     "httpStatus": 400,
        #     "message": "No se formulo bien la peticion"
        # }
        # try:
        #     if request.headers['user-token']:
        #         profile_user = get_profile_user_arc(request.headers['user-token'], request.headers['site'])
        #         if profile_user.get('httpStatus'):
        #             data_response = {
        #                 "httpStatus": profile_user.get('httpStatus'),
        #                 "message": "Token incorrecto"
        #             }
        #             return JsonResponse(data_response)
        #     else:
        #         return JsonResponse(data_response)
        # except Exception:
        #     capture_exception()
        #     return JsonResponse(data_response)

        arc_user = get_arc_user_by_token(request=request)
        if not arc_user:
            return JsonResponse({
                "httpStatus": 401,
                "message": "Token incorrecto"
            })

        domains = Domain.objects.all()
        list_domain = []
        for domain in domains:
            list_domain.append(domain.name)

        result = {
            'domains': list_domain,
        }
        return Response(
            result,
            status=status.HTTP_200_OK
        )
