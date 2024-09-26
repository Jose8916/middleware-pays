import json
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from sentry_sdk import capture_message, capture_event, push_scope, capture_exception

from apps.pagoefectivo.models import PaymentNotification, CIP
from apps.arcsubs.models import ArcUser
from apps.paywall.models import Subscription
from apps.paywall.arc_clients import IdentityClient, search_user_arc_param, SaleLinked
from apps.paywall.google_analytics_clients import send_google_anlytics, send_google_anlytics_ecommerce
from apps.paywall.classes.history_state import HistoryState
from apps.paywall.shortcuts import render_send_email
import requests


class ApiPagoEfectivoNotificationView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        """
            Procesa los eventos de notificación de pago efectivo
        """
        data = request.data
        data_json = data.get('data', '')
        try:
            cip_obj = CIP.objects.get(
                cip=data_json.get('cip', ''),
            )
        except Exception:
            cip_obj = None

        try:
            arc_user = cip_obj.arc_user
        except Exception:
            arc_user = None

        payment = PaymentNotification(
            event_type=data.get('eventType', ''),
            operation_number=data.get('operationNumber', ''),
            cip=data_json.get('cip', ''),
            currency=data_json.get('currency', ''),
            amount=data_json.get('amount', ''),
            payment_date=data_json.get('paymentDate', ''),
            transaction_code=data_json.get('transactionCode', ''),
            data=data.get('data', {}),
            arc_user=arc_user,
            sub_type=PaymentNotification.REGULAR_STATE,
            cip_obj=cip_obj
        )
        payment.save()

        if data.get('eventType', '') == 'cip.paid':
            cip_obj.state = CIP.STATE_CANCELLED
            cip_obj.save()
            action = cip_obj.plan.get_frequency_name() + ' | PE - ' + data_json.get('cip', '')
            # envio google analitycs
            send_google_anlytics(
                'P3_Plan_Digital',  # category
                action,  # action
                '',  # Etiqueta
                int(cip_obj.amount),  # event_value
                cip_obj.plan.partner.partner_code,  # brand
                arc_user.uuid,  # uuid
                'event'  # Event hit type.
            )

            sales_linked = SaleLinked(cip_obj.plan.partner.partner_code)
            response, dict_fields = sales_linked.create(
                'pagoefectivo',
                arc_user.uuid,
                cip_obj.plan.arc_pricecode,
                cip_obj.plan.product.arc_sku
            )
            if response:
                if (response.status_code <= 299) and (response.status_code >= 200):
                    # actualizar en el evento
                    # subscription = Subscription.objects.get(arc_id=response_dict.get('subscriptionID'))
                    # cip_obj.subscription = subscription
                    cip_obj.linked = CIP.LINKEADO
                else:
                    cip_obj.linked = CIP.ERROR_EN_LINKEO
            else:
                cip_obj.linked = CIP.LINKED_NO_ENVIADO
            cip_obj.linked_request = dict_fields.get('body', '')
            response_linked = dict_fields.get('response', '')
            cip_obj.linked_response = response_linked
            cip_obj.subscription_arc_id = response_linked.get('subscriptionID', '')
            cip_obj.save()

        return Response(
            {
                "httpStatus": 200,
                "message": "Se registro correctamente",
                "status": True,
            },
            status=status.HTTP_200_OK
        )

