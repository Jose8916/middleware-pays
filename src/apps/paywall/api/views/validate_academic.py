import json

from django.http import JsonResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from sentry_sdk import capture_event

from ...paywall_utils import get_arc_user_by_token
from ...utils import random_characters, sum_days, validar_email
from apps.paywall.models import HashCollegeStudent, Domain, Campaign, Partner
from apps.paywall.shortcuts import render_send_email


class ValidateUsersAcademicAPIView(APIView):
    permission_classes = (AllowAny, )

    def post(self, request):
        """
        Genera el token para consultar si un DNI es suscriptor.

        Cabecera HTTP:
        - user-token: 'access_token' de ARC
        - Arc-Site: Site de ARC (gestion | elcomercio)
        """

        # # Validar datos para evitar injections
        body = request.body.decode('utf-8')
        received_json_data = json.loads(body)
        email = received_json_data.get('correo', '')
        if email:
            email = email.lower()
        site = request.headers.get('site', '')

        # Validate User - Token Access
        arc_user = get_arc_user_by_token(request=request, site=site)

        if not arc_user:
            return self.response_error(message='Su sesión ha expirado')

        # Valida que el email sea correcto
        if not validar_email(email):
            return self.response_error('Email inválido')

        # Valida que el dominio sea de universidad
        domain = email.split('@')[1].lower()
        if not Domain.objects.filter(name=domain).exists():
            return self.response_error('El correo no pertenece a una Universidad asociada')

        partner = Partner.objects.get(partner_code=site)
        # Valida el número de intentos del usuario
        intentos = HashCollegeStudent.objects.filter(arc_user=arc_user, site=partner).count()
        if intentos > 5:
            return self.response_error('Superó el número de intentos permitidos')

        campaign = Campaign.objects.get_by_offer(site=site, offer=Campaign.OFFER_UNIVERSITY)
        # Valida que el correo no usó el descuento
        if HashCollegeStudent.objects.filter(
            email=email.lower(),
            user_offer__campaign=campaign,
            user_offer__subscription__isnull=False,
        ).exists():
            return self.response_error('Su correo ya accedíó al descuento')

        hash_college = HashCollegeStudent.objects.filter(
            arc_user=arc_user,
            email=email.lower(),
            site=partner,
            user_offer__campaign__is_active=True
        ).last()

        if not hash_college:
            hash_college = HashCollegeStudent.objects.create(
                arc_user=arc_user,
                email=email.lower(),
                site=partner,
                hash_user=random_characters(8),
                date_expire=sum_days(3),
                date_birth=received_json_data.get('date_birth', ''),
                degree=received_json_data.get('degree', '')
            )

        if hash_college:
            hash_college.date_birth = received_json_data.get('date_birth', '')
            hash_college.degree = received_json_data.get('degree', '')
            hash_college.save()

        setting_legal = {
            'terms': partner.terms_of_service_url,
            'policies_privacy': partner.privacy_policy_url,
            'frequent_questions': partner.faq_url
        }

        subject = '[{name}] Plan Universitario'.format(name=partner.partner_name.upper())
        template = 'mailings/%s/%s.html' % (site, 'validate_academic')
        data = {
            'hash_user': hash_college.hash_user,
            'us_fullname': arc_user.get_full_name(),
            'email_arc': arc_user.email,
            'legal': setting_legal,
        }
        from_email = '{name_sender} <{direction_sender}>'.format(
            name_sender=partner.partner_name,
            direction_sender=partner.promotional_sender
        )
        render_send_email(
            template_name=template,
            subject=subject,
            to_emails=email,
            from_email=from_email,
            context=data,
        )
        return JsonResponse({"httpStatus": 200, "message": 'Revise su correo', "status": True})

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
