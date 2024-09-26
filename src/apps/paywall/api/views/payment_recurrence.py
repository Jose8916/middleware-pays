from django.conf import settings

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from sentry_sdk import capture_exception

from ...models import Subscription, FailRenewSubscription
from apps.paywall.shortcuts import render_send_email
# from apps.clubelcomercio.utils import send_renew_subscription_to_club


class ApiPaymentRecurrenceView(APIView):

    def post(self, request):
        """
            Procesa los eventos RENEW_SUBSCRIPTION

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

        subscription, created_subs = Subscription.objects.get_or_create_subs(
            site=params['site'],
            subscription_id=params['subscription'],
            sync_data=True
        )

        for payment, created in subscription.get_or_create_payments():
            if created:
                # send_renew_subscription_to_club(subscription)
                self.send_mail_notification(subscription, payment)

        return Response(
            {'suscription': subscription.arc_id, },
            status=status.HTTP_200_OK
        )

    def send_mail_notification(self, subscription, payment):
        partner = subscription.partner
        plan = subscription.plan

        payment_partner = subscription.data['currentPaymentMethod']['paymentPartner']
        if payment_partner != 'Free' and payment_partner != 'Linked':
            card_number = '**** **** **** {}'.format(subscription.data['currentPaymentMethod']['lastFour'])
        else:
            card_number = ''

        setting_legal = {
            'terms': partner.terms_of_service_url,
            'policies_privacy': partner.privacy_policy_url,
            'frequent_questions': partner.faq_url
        }

        product_name = '{} - {}'.format(plan.product.prod_name, plan.get_frequency_name())

        email = subscription.get_email()

        data = {
            'card_number': card_number,
            'legal': setting_legal,
            'product': product_name,
            'rate_description': '',  # plan.get_rate_description(),
            'site': partner.partner_code,
            'site_name': partner.partner_name,
            'total': '{:0,.2f}'.format(payment.pa_amount),
            'url_base': settings.PAYWALL_MAILING_ASSETS_URL,
            'us_email': email,
            'us_fullname': subscription.get_full_name(),
        }

        template_name = 'mailings/%s/subscription_recurrence.html' % partner.partner_code
        subject = '[%s] Renovación de tu Suscripción - %s' % (partner.partner_name, plan.product.prod_name)
        from_email = '{name_sender} <{direction_sender}>'.format(
            name_sender=partner.partner_name,
            direction_sender=partner.transactional_sender
        )
        render_send_email(
            template_name=template_name,
            subject=subject,
            to_emails=email,
            from_email=from_email,
            context=data,
        )
