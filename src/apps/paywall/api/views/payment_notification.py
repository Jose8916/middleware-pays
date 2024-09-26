import json
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from sentry_sdk import capture_message, capture_event, push_scope, capture_exception

from apps.clubelcomercio.models import ClubSubscription
from apps.paywall.arc_clients import IdentityClient, search_user_arc_param
from apps.paywall.classes.history_state import HistoryState
from apps.paywall.classes.collaborator_management import CollaboratorManagement
from apps.paywall.models import Subscription, UserTermsConditionPoliPriv, PaymentProfile, ArcUser, PaymentTracking
from apps.paywall.shortcuts import render_send_email
from apps.pagoefectivo.models import CIP
from django.conf import settings


class ApiPaymentNotificationView(APIView):

    def post(self, request):
        """
            Procesa los eventos START_SUBSCRIPTION

            Parámetros:
            - suscription_id: ID de la suscripción de ARC.
            - site: comercio | gestion
        """
        data = request.data
        site = data.get('site')

        if 'site' not in data or 'suscription_id' not in data:
            capture_event(
                {
                    'message': 'START_SUBSCRIPTION Wrong Parameters',
                    'extra': {
                        'data': data
                    }
                }
            )
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

        for payment, created in subscription.get_or_create_payments():

            if created:  # Envía email de bienvenida
                self.update_foreignkey_payment_tracking(subscription, payment)
                self.send_mail_notifications(subscription, payment)

                self.register_term_and_conditions(subscription=subscription, payment=payment)

        if created_sub and not subscription.get_or_create_payments():
            # Si no tiene payments, sólo envía el email del editor.
            try:
                self.send_mail_notifications(subscription)
            except:
                capture_exception()

        send_pe = False
        if subscription.by_linked_method():
            try:
                cip = CIP.objects.get(
                    subscription_arc_id=str(subscription.arc_id),
                )
            except Exception:
                cip = ''

            if cip:
                cip.subscription = subscription
                cip.save()
                subscription.payment_profile = cip.payment_profile
                subscription.save()

            if CIP.objects.filter(subscription=subscription, state=CIP.STATE_CANCELLED).exists():
                send_pe = True

        # Activa la suscripcion de Club
        if subscription.by_payu_method() or send_pe:
            club_subscription = ClubSubscription.objects.create(
                subscription=subscription
            )
            club_subscription.club_activate()

        # Enlaza la suscripcion a los colaboradores.
        collaborator = CollaboratorManagement()
        collaborator.link_subscription(subscription)

        return Response(
            {'suscription': subscription.arc_id, },
            status=status.HTTP_200_OK
        )

    def update_foreignkey_payment_tracking(self, subscription, payment):
        try:
            if payment.pa_origin == 'WEB':
                arc_user = ArcUser.objects.get(uuid=subscription.arc_user.uuid)
                PaymentTracking.objects.filter(arc_order=payment.arc_order).update(
                    arc_user=arc_user,
                    subscription=subscription,
                    payment=payment,
                    partner=subscription.partner
                )

        except Exception as e:
            with push_scope() as scope:
                scope.set_tag("id_subscription", subscription.arc_id)
                scope.level = 'error'
                capture_event(
                    {
                        'message': 'Error al actualizar el tracking',
                        'extra': {
                            'subscription': subscription,
                            'payment': payment,
                            'error': e
                        }
                    }
                )
            pass

    def register_term_and_conditions(self, subscription, payment):
        if UserTermsConditionPoliPriv.objects.filter(
            user_uuid=subscription.arc_user.uuid, arc_order=payment.arc_order
        ).exists():
            term_and_conditions = UserTermsConditionPoliPriv.objects.filter(
                user_uuid=subscription.arc_user.uuid, arc_order=payment.arc_order
            ).update(complete=True)

            PaymentProfile.objects.filter(
                id=subscription.payment_profile.id
            ).update(user_terms_condition_pp=term_and_conditions)

    def send_mail_notifications(self, subscription, payment=None):
        partner = subscription.partner
        plan = subscription.plan

        payment_partner = subscription.data['currentPaymentMethod']['paymentPartner']
        if payment_partner != 'Free' and payment_partner != 'Linked':
            card_number = '******' + subscription.data['currentPaymentMethod']['lastFour']
        else:
            card_number = ''

        setting_legal = {
            'terms': partner.terms_of_service_url,
            'policies_privacy': partner.privacy_policy_url,
            'frequent_questions': partner.faq_url
        }

        data = IdentityClient().get_profile_by_uuid(subscription.arc_user.uuid)
        user_arc = search_user_arc_param('uuid', subscription.arc_user.uuid)
        only_facebook = ''
        with_facebook = ''
        login_email = data.get('email', '')

        if user_arc.get('totalCount', ''):
            result = user_arc.get('result', '')[0]
            identities = []
            for identity in result.get('identities'):
                identities.append(identity.get('type'))

            if len(identities) == 1 and 'Facebook' in identities:
                only_facebook = 1

            if login_email and len(identities) > 1 and 'Facebook' in identities:
                with_facebook = 1

        without_email = ''
        if not data.get('email') and '@' not in data.get('email'):
            without_email = 1

        try:
            product_name = '{} - {}'.format(plan.product.prod_name, plan.get_frequency_name())
        except Exception:
            product_name = ''

        try:
            plan_name = plan.data.get('description', '{}').replace('</p>', '').replace('<p>', '').replace('\n', '') \
                .replace('&nbsp;', '')
            plan_title = json.loads(plan_name).get('plan_title', '')
        except Exception:
            plan_title = ''

        email = subscription.get_email()

        data = {
            'card_number': card_number,
            'legal': setting_legal,
            'product': plan_title if plan_title else product_name,
            'rate_description': plan.get_rate_description(),
            'site': partner.partner_code,
            'site_name': partner.partner_name,
            'site_url': partner.partner_host,
            'total': '{:0,.2f}'.format(payment.pa_amount) if payment else None,
            'url_base': settings.PAYWALL_MAILING_ASSETS_URL,
            'us_email': email,
            'us_fullname': subscription.get_full_name(),
            'only_facebook': only_facebook,
            'without_email': without_email,
            'login_email': login_email,
            'with_facebook': with_facebook
        }

        from_email = '{name_sender} <{direction_sender}>'.format(
            name_sender=partner.partner_name,
            direction_sender=partner.transactional_sender
        )

        if payment:
            welcome_template = 'mailings/%s/subscription_confirmation.html' % partner.partner_code
            welcome_subject = '[{}] Confirmación de tu Suscripción - {}'.format(
                partner.partner_name.upper(),
                plan_title if plan_title else plan.product.prod_name
            )

            render_send_email(
                template_name=welcome_template,
                subject=welcome_subject,
                to_emails=email,
                from_email=from_email,
                context=data,
            )

        invoice_template = 'mailings/%s/subscription_director.html' % partner.partner_code
        invoice_subject = '[{}] Mensaje de bienvenida'.format(partner.partner_name.upper())

        render_send_email(
            template_name=invoice_template,
            subject=invoice_subject,
            to_emails=email,
            from_email=from_email,
            context=data,
        )
