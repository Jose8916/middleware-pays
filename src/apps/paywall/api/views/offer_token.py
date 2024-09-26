from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models import OfferToken
from ...paywall_utils import get_arc_user_by_token


class OfferTokenAPIView(APIView):
    permission_classes = (AllowAny, )

    def post(self, request):
        """
        Genera el token para consultar si un DNI es suscriptor.

        HTTP headers:
        - user-token: 'access_token' de ARC
        - Arc-Site: Site de ARC (gestion | elcomercio)
        """

        # validate User - Token Access
        arc_user = get_arc_user_by_token(request)

        if not arc_user:
            return Response(
                {'error': 'Permisos incorrectos'},
                status=status.HTTP_400_BAD_REQUEST
            )

        offer_token, created = OfferToken.objects.get_or_create(user_uuid=arc_user.uuid)

        result = {
            'token': offer_token.token,
        }
        return Response(
            result,
            status=status.HTTP_200_OK
        )
