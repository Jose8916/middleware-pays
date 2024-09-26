import json
from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from sentry_sdk import capture_message, capture_event, push_scope, capture_exception

from rest_framework.permissions import AllowAny

from apps.pagoefectivo.forms import CIPForm, PaymentTrackingPEForm
from apps.paywall.forms import PaymentProfileForm
from datetime import datetime
from apps.pagoefectivo.pe_clients import PESalesClient
from apps.paywall.models import PaymentProfile


class ApiCIPCreationView(APIView):
    permission_classes = (AllowAny,)

    def update_fields(self, data):
        data_profile = {
            'uuid': data.get('user_id', None),
            'prof_name': data.get('user_name', None),
            'prof_lastname': data.get('lastname_father', None),
            'prof_lastname_mother': data.get('lastname_mother', None),
            'prof_doc_type': data.get('user_document_type', None),
            'prof_doc_num': data.get('user_document_number', None),
            'prof_phone': data.get('user_phone', None),
            'portal_email': data.get('user_email', None)
        }

        return data_profile

    def date_expiry(self, date_expiry):
        if date_expiry:
            date_expiry_array = date_expiry.split('-05:00')
            return date_expiry_array[0]
        else:
            now = datetime.now()
            return now.strftime("%Y-%m-%d %H:%M:%S")

    def post(self, request):
        """
            Llama al servicio de generacion de CIPs de pago efectivo
        """
        form_tracking = PaymentTrackingPEForm(request.data)
        if form_tracking.is_valid():
            payment_tracking = form_tracking.save()
        else:
            return Response(form_tracking.errors, status=status.HTTP_400_BAD_REQUEST)

        data_profile = self.update_fields(request.data)
        form_payment = PaymentProfileForm(data_profile)

        if form_payment.is_valid():
            form_payment_obj = form_payment.get()

            if not form_payment_obj:
                form_payment_obj = form_payment.save()

            form_cip = CIPForm(request.data)

            if form_cip.is_valid():
                cip_obj = form_cip.save(commit=False)
                cip_obj.payment_profile = form_payment_obj
                cip_obj.payment_tracking_pe = payment_tracking
                cip_obj.save()

                pe_client = PESalesClient()
                response, dict_fields = pe_client.create_cip(
                    cip_obj=cip_obj,
                    cd=form_cip.cleaned_data,
                    date_expiry=request.data.get('date_expiry', ''),
                    token=request.data.get('token', '')
                )
                if response:
                    if (response.status_code <= 299) and (response.status_code >= 200):
                        form_cip.update(
                            response=response,
                            cip=cip_obj
                        )
                        return Response(dict_fields, status=status.HTTP_200_OK)
                    else:
                        return Response(dict_fields, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response(dict_fields, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(form_cip.errors, status=status.HTTP_400_BAD_REQUEST)
