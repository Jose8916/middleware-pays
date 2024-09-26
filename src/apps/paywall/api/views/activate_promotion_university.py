import json

from django.http import JsonResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ...paywall_utils import get_arc_user_by_token
from apps.paywall.models import HashCollegeStudent, UserOffer, Partner


class ActivatePromotionAPIView(APIView):
    permission_classes = (AllowAny, )

    def post(self, request):
        """
        Genera el token para consultar si un DNI es suscriptor.

        Cabecera HTTP:
        - user-token: 'access_token' de ARC
        - Arc-Site: Site de ARC (gestion | elcomercio)
        """

        # validate User - Token Access
        arc_user = get_arc_user_by_token(request=request)
        arc_site = request.headers.get('site', '')

        if not arc_user:
            return self.response_error(message='Su sesión ha expirado')

        body = request.body.decode('utf-8')
        received_json_data = json.loads(body)
        hash_user = received_json_data.get('hash_user')

        if not hash_user:
            return self.response_error(message='Debe ingresar un código')

        partner = Partner.objects.get(partner_code=arc_site)

        try:
            hash_college = HashCollegeStudent.objects.get(
                arc_user=arc_user,
                hash_user=hash_user,
                site=partner,
                email=received_json_data.get('email', '').lower(),
            )

        except HashCollegeStudent.DoesNotExist:
            return self.response_error(message='Código incorrecto')

        else:
            if not hash_college.user_offer:
                hash_college.user_offer, created = UserOffer.objects.get_or_create_promo(
                    site=arc_site,
                    arc_user=arc_user,
                    offer=UserOffer.OFFER_UNIVERSITY,
                )

            if hash_college.user_offer.subscription_id:
                return self.response_error(message='Ya usó el descuento')

            else:
                hash_college.save()

                return JsonResponse(
                    {
                        "httpStatus": 200,
                        "token": hash_college.user_offer.token,
                        "status": True,
                        "code": "200a",
                    }
                )

    def response_error(self, message):
        return Response(
            {
                "httpStatus": 400,
                "message": message,
                "status": False,
                "code": "100a",
            },
            status=status.HTTP_400_BAD_REQUEST
        )
