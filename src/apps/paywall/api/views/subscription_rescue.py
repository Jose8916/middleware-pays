from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.paywall.models import Subscription, UserTermsConditionPoliPriv, PaymentProfile
from apps.paywall.classes.history_state import HistoryState


class ApiRescueSubscriptionNotificationView(APIView):

    def post(self, request):
        """
            Procesa el evento RESCUE_SUBSCRIPTION

            Parámetros:
            - suscription_id: ID de la suscripción de ARC.
            - site: comercio | gestion
        """
        data = request.data
        site = data.get('site')

        if 'site' not in data or 'suscription_id' not in data:
            return Response(
                {'error': 'Parámetros incompletos.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription, created_sub = Subscription.objects.get_or_create_subs(
            site=site,
            subscription_id=data['suscription_id'],
            sync_data=True,
        )
        history_state = HistoryState(subscription)
        history_state.update_data()

        return Response(
            {'suscription': subscription.arc_id, },
            status=status.HTTP_200_OK
        )

    def send_mail_notifications(self, subscription, payment=None):
        # mail de restauracion de suscripcion
        print('mail de restauracion de suscripcion')