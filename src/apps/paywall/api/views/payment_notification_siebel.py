import json
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from sentry_sdk import capture_message, capture_event, push_scope, capture_exception

from apps.clubelcomercio.models import ClubSubscription
from apps.paywall.forms import SiebelConfirmationPaymentForm
from apps.paywall.arc_clients import IdentityClient, search_user_arc_param
from apps.paywall.classes.history_state import HistoryState
from apps.paywall.models import Subscription, UserTermsConditionPoliPriv, PaymentProfile, ArcUser, PaymentTracking
from apps.siebel.models import SiebelConfirmationPayment


class NotificationPaymentSiebelView(APIView):

    def post(self, request):
        """
            Procesa los eventos de siebel

        """

        form_confirmation = SiebelConfirmationPaymentForm(request.data)

        if form_confirmation.is_valid():
            cip_obj = form_confirmation.save(commit=False)
            cip_obj.log_response = request.data
            cip_obj.save()
            if cip_obj:
                result = {
                    'status': True,
                    'mensaje': 'Correcto'
                }
                return Response(
                    result,
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'status': False,
                        'mensaje': 'Solicitud Fallida'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            result = dict(status=False, mensaje=form_confirmation.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)