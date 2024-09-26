import json

from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from sentry_sdk import capture_exception

from apps.paywall.models import UserTermsConditionPoliPriv, TermsConditionsPoliPriv
from apps.paywall.paywall_utils import get_arc_user_by_token


class TermsAndConditionsApiView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        """
            Registration of terms and conditions

            :parameter:
            - uuid
            - order
            - tyc
        """

        # data_response = {
        #     "httpStatus": 400,
        #     "message": "No se formulo bien la peticion"
        # }
        # if request.headers['user-token']:
        #     profile_user = get_profile_user_arc(request.headers['user-token'], request.headers['site'])
        #     if profile_user.get('httpStatus'):
        #         data_response = {
        #             "httpStatus": profile_user.get('httpStatus'),
        #             "message": "Token incorrecto"
        #         }
        #         return JsonResponse(data_response)
        # else:
        #     return JsonResponse(data_response)

        arc_user = get_arc_user_by_token(request=request)
        if not arc_user:
            return JsonResponse({
                "httpStatus": 401,
                "message": "Token incorrecto"
            })

        body = request.body.decode('utf-8')
        received_json_data = json.loads(body)

        try:
            term_and_cond = TermsConditionsPoliPriv.objects.get(partner__partner_code=request.headers['site'], state=True)
        except Exception:
            capture_exception()
            return JsonResponse({"httpStatus": 400, "message": 'No existe la marca'})

        terms_conditions = UserTermsConditionPoliPriv(
            user_uuid=received_json_data.get('uuid', ''),
            arc_order=received_json_data.get('order', ''),
            tyc_value=received_json_data.get('tyc', ''),
            complete=False,
            tyc_pp=term_and_cond
        )

        try:
            terms_conditions.save()
        except Exception:
            capture_exception()
            return JsonResponse({"httpStatus": 400, "message": 'Error'})

        else:
            return JsonResponse({"httpStatus": 200, "message": "Éxito"})
