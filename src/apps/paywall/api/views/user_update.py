from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from sentry_sdk import capture_message, capture_event, push_scope, capture_exception

from apps.clubelcomercio.models import ClubSubscription
from apps.paywall.arc_clients import IdentityClient, search_user_arc_param
from apps.paywall.classes.history_state import HistoryState
from apps.paywall.models import Subscription, UserTermsConditionPoliPriv, PaymentProfile, ArcUser, PaymentTracking


class UserUpdateView(APIView):

    def post(self, request):
        """
            Actualizacion de data user

            Parámetros:
            - suscription_id: ID de la suscripción de ARC.
            - site: comercio | gestion
        """
        if request.data.get('event', '') == 'EMAIL_VERIFIED' and request.data.get('uuid', ''):
            uuid = request.data.get('uuid', '')
            profile = IdentityClient().get_profile_by_uuid(uuid=uuid)
            ArcUser.objects.filter(uuid=uuid).update(
                data=profile,
                email=profile.get('email')
            )
            return Response(
                {'uuid': uuid, },
                status=status.HTTP_200_OK
            )
