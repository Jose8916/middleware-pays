import json
import requests as request_post

from django.conf import settings
from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from sentry_sdk import capture_exception

from apps.paywall.models import Corporate, Partner
from apps.paywall.shortcuts import render_send_email
from apps.paywall.forms import FormWithCaptcha
from apps.paywall.paywall_utils import get_arc_user_by_token


class SuscripcionCorporativaApiView(APIView):
    permission_classes = (AllowAny,)

    def get_celular(self, received_json_data):
        if received_json_data.get('telefono', ''):
            telefono = received_json_data.get('telefono', '')

        elif received_json_data.get('asunto', ''):
            telefono = received_json_data.get('asunto', '')

        else:
            telefono = ''

        return telefono

    def post(self, request, *args, **kwargs):
        """
            Registra las solicitudes corporativas.

            Parámetros:
            - correo
            - nombre
            - apellido
            - tipo_consulta
            - organizacion
            - asunto
            - descripcion
        """

        # arc_user = get_arc_user_by_token(request=request)

        body = request.body.decode('utf-8')
        received_json_data = json.loads(body)

        # if arc_user:
        #     is_valid = True
        # else:
        #     is_valid = self.valid_captcha(received_json_data)
        #     # form = FormWithCaptcha(request.POST)
        #     # is_valid = form.is_valid()
        is_valid = self.valid_captcha(received_json_data)

        if is_valid:
            tipo_consulta = dict(Corporate._meta.get_field('corp_type').choices)

            subject = 'Consulta - Suscripción corporativa'
            site = request.headers['site']
            tpl = 'mailings/%s/%s.html' % (site, 'corporate_subscriptions_info')

            correo = received_json_data.get('correo', '').lower()

            data = {
                'corp_email': correo,
                'corp_name': received_json_data.get('nombre', ''),
                'corp_lastname': received_json_data.get('apellido', ''),
                'corp_type': tipo_consulta.get(received_json_data.get('tipo_consulta', ''), ''),
                'corp_organization': received_json_data.get('organizacion', ''),
                'telefono': self.get_celular(received_json_data),
                'corp_detail': received_json_data.get('descripcion', '')
            }

            to_emails = [correo, ] if correo.endswith('@mailinator.com') else settings.PAYWALL_CONTACT_US
            try:
                partner = Partner.objects.get(partner_code=site)
            except Exception:
                partner = None
            if partner:
                from_email = '{name_sender} <{direction_sender}>'.format(
                    name_sender=partner.partner_name,
                    direction_sender=partner.transactional_sender
                )
            else:
                from_email = None

            render_send_email(
                template_name=tpl,
                subject=subject,
                to_emails=to_emails,
                from_email=from_email,
                context=data
            )

            corporate = Corporate(
                state=True,
                corp_email=received_json_data.get('correo', ''),
                corp_name=received_json_data.get('nombre', ''),
                corp_lastname=received_json_data.get('apellido', ''),
                corp_type=received_json_data.get('tipo_consulta', ''),
                corp_organization=received_json_data.get('organizacion', ''),
                telefono=self.get_celular(received_json_data),
                corp_detail=received_json_data.get('descripcion', ''),
                site=partner
            )

            try:
                corporate.save()

            except Exception:
                capture_exception()
                result = {"httpStatus": 400, "message": 'Error'}
                return Response(
                    result,
                    status=status.HTTP_400_BAD_REQUEST
                )

            else:
                return JsonResponse({"httpStatus": 200, "message": "Éxito"})
        else:

            result = {"httpStatus": 400, "code": "wrong_captcha", "message": 'Captcha incorrecto'}
            return Response(
                result,
                status=status.HTTP_400_BAD_REQUEST
            )

    def valid_captcha(self, data):
        recaptcha_response = data.get('g-recaptcha-response', '')
        data = {
            'secret': settings.RECAPTCHA_PRIVATE_KEY,
            'response': recaptcha_response
        }

        r = request_post.post('https://www.google.com/recaptcha/api/siteverify', data=data)
        result = r.json()
        ''' End reCAPTCHA validation '''

        if result['success']:
            is_valid = True
        else:
            is_valid = False

        return is_valid