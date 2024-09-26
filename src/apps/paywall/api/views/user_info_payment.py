from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models import Subscription
from ...paywall_utils import get_arc_user_by_token


class ApiUserInfoPayment(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, subscription_id):
        # validate User - Token Access

        arc_user = get_arc_user_by_token(request)

        if not arc_user:
            return Response(
                {'error': 'Permisos incorrectos'},
                status=status.HTTP_400_BAD_REQUEST
            )

        else:
            try:
                subscription = Subscription.objects.get(
                    arc_user_id=arc_user.id,
                    arc_id=subscription_id
                )

            except Subscription.DoesNotExist:
                return Response(
                    {'error': 'No existe la suscripción'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            except Exception:
                return Response(
                    {'error': 'Error al devolver la info'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            else:
                response = {
                    'email': subscription.payment_profile.arc_user.email,
                    'doc_type': subscription.payment_profile.prof_doc_type,
                    'doc_number': subscription.payment_profile.prof_doc_num,
                    'name': subscription.payment_profile.prof_name,
                    'lastname': '{} {}'.format(
                        subscription.payment_profile.prof_lastname,
                        subscription.payment_profile.prof_lastname_mother or ''
                    ),
                    'phone': subscription.payment_profile.prof_phone,
                }
                return Response(
                    response,
                    status=status.HTTP_200_OK
                )
