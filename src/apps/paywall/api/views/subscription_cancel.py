from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.paywall.models import Subscription
from apps.paywall.shortcuts import render_send_email
from apps.paywall.classes.history_state import HistoryState


class ApiSubscriptionCancelView(APIView):
    TYPE_LINKED = 'Linked'

    def post(self, request):
        """
            Procesa los eventos CANCEL_SUBSCRIPTION

            Parámetros:
            - suscription: ID de la suscripción de ARC.
            - site: comercio | gestion
        """

        params = request.data

        if 'site' not in params or 'subscription' not in params:
            return Response(
                {'error': 'Parámetros incompletos.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription, _ = Subscription.objects.get_or_create_subs(
            site=params['site'],
            subscription_id=params['subscription'],
            sync_data=False,  # Usa datos de la base de datos
        )
        initial_state = subscription.state
        subscription.sync_data()  # Descarga los datos de ARC

        history_state = HistoryState(subscription)
        history_state.update_data()

        if not subscription.by_linked_method():
            # Valida que el estado cambió y que la suscripción no esté activa.
            last_state = subscription.state
            if (
                initial_state != last_state and
                last_state != Subscription.ARC_STATE_ACTIVE
            ):
                self.send_mail_cancel(subscription)

        return Response(
            {
                'suscription': subscription.arc_id
            },
            status=status.HTTP_200_OK
        )

    def send_mail_cancel(self, subscription):

        partner = subscription.partner
        profile = subscription.arc_user

        setting_legal = {
            'terms': partner.terms_of_service_url,
            'policies_privacy': partner.privacy_policy_url,
            'frequent_questions': partner.faq_url
        }

        fullname = subscription.payment_profile.get_full_name() if subscription.payment_profile else ''

        data = {
            'url_base': settings.PAYWALL_MAILING_ASSETS_URL,
            'site': partner.partner_code,
            'us_fullname': fullname,
            'legal': setting_legal
        }

        template_name = 'mailings/%s/subscription_cancel.html' % partner.partner_code
        subject = '[%s] Anulación de tu Suscripción' % partner.partner_name.upper()

        from_email = '{name_sender} <{direction_sender}>'.format(
            name_sender=partner.partner_name,
            direction_sender=partner.transactional_sender
        )

        render_send_email(
            template_name=template_name,
            subject=subject,
            to_emails=subscription.payment_profile.portal_email,
            from_email=from_email,
            context=data,
        )
