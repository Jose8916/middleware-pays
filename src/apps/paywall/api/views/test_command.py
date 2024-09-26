import json

from datetime import datetime
from django.http import JsonResponse
from django.utils.timezone import get_default_timezone
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from apps.paywall.models import Subscription, Operation, Log
from apps.paywall.utils_report_subscription import UsersSubscription
from django.db.models import Q

from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, SiebelConfirmationPayment
from ...utils_siebel import SiebelConciliationSender
from datetime import datetime, timedelta
from django.db.models import Count
from apps.paywall.arc_clients import SalesClient


class TestCommandApiView(APIView):

    def post(self, request, *args, **kwargs):
        """
        Retorna los datos de las suscripciones para datawarehouse.

        Parámetros:
        - date_start: Fecha de inicio en formato %Y-%m-%d
        - date_end: Fecha de fin en formato %Y-%m-%d
        """
        enviado = ''
        operation_list = []
        list_reason = []

        operation_list = Operation.objects.filter(
            payment__subscription__arc_id=6269097765365606,
            conciliation_siebel_hits__lte=11,
            payment__pa_origin='WEB',
            ope_amount__gte=5
        ).filter(
            Q(conciliation_cod_response__isnull=True) | Q(conciliation_cod_response='')
            | Q(conciliation_cod_response__exact='') | Q(conciliation_cod_response='0')
            | Q(conciliation_cod_response__exact='0') | Q(conciliation_cod_response=0)
        ).exclude(
            recurrencia_response__contains='Correcto',
            conciliation_siebel_response__contains='ya se encuentra registrado',
        ).order_by('payment__date_payment')

        for operation in operation_list:
            if not SalesClient().has_a_refund(operation.payment.partner.partner_code, operation.payment.arc_order):

                enviado = operation.id
                siebel_client = SiebelConciliationSender(operation)

                try:
                    siebel_client.send_conciliation()
                except Exception:
                    capture_exception()
        return JsonResponse(
            {
                "httpStatus": 200,
                "status": enviado,
                "code": "200a",
            }
        )


class TestWebhookPianoApiView(APIView):
    permission_classes = (AllowAny, )

    def get(self, request, *args, **kwargs):
        # arc_user = get_arc_user_by_token(request=request)

        #body = request.META
        #if body:

        b = Log(text_log=request.GET.get('data'))
        b.save()
        return JsonResponse(
            {
                "httpStatus": 200,
                "code": "200a",
            }
        )
    
    """
    def post(self, request, *args, **kwargs):
        # arc_user = get_arc_user_by_token(request=request)

        # body = request.body.decode('utf-8')

        body = request.POST.get('data')
        if body:
            b = Log(text_log=body)
            b.save()
        return JsonResponse(
            {
                "httpStatus": 200,
                "code": "200a",
            }
        )
    """

class TestPaymentCommandApiView(APIView):

    def post(self, request, *args, **kwargs):
        current_month = datetime.now().month


        operation_list = []
        list_reason = []

        operation_list = Operation.objects.filter(
            ope_amount__gte=5,
            payment__pa_origin='RECURRENCE',
            payment_profile__siebel_entecode__isnull=False,
            payment_profile__siebel_entedireccion__isnull=False,
            payment__subscription__delivery=616162
        ).filter(
            Q(conciliation_cod_response__isnull=True) | Q(conciliation_cod_response='')
            | Q(conciliation_cod_response__exact='') | Q(conciliation_cod_response='0')
            | Q(conciliation_cod_response__exact='0') | Q(conciliation_cod_response=0)
        ).exclude(recurrencia_response__contains='Correcto'). \
            exclude(conciliation_siebel_response__contains='ya se encuentra registrado')

        for reason in list_reason:
            operation_list = operation_list.exclude(payment__subscription__motive_anulled__contains=reason)

        operation_list = operation_list.order_by('payment__date_payment')

        for operation in operation_list:
            if not SalesClient().has_a_refund(operation.payment.partner.partner_code, operation.payment.arc_order):
                mirando = operation.id
                siebel_client = SiebelConciliationSender(operation)

                try:
                    siebel_client.send_payment()
                except Exception:
                    capture_exception()

        return JsonResponse(
            {
                "httpStatus": 200,
                "status": mirando,
                "code": "200a",
            }
        )
