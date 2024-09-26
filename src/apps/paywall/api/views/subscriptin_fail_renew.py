"""
    API para procesar los eventos de errores de cobro
"""

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from sentry_sdk import capture_exception, capture_event

# from apps.clubelcomercio.utils import send_terminate_subscription_to_club
from ...models import Subscription, FailRenewSubscription, TypeOfLowSubscription, LowBySuspension, EventTypeSuspension
from apps.arcsubs.models import Event
from apps.clubelcomercio.models import ClubSubscription
from apps.paywall.arc_clients import SalesClient
from apps.siebel.clients.unsubscribe import UnsubscribeClient
from apps.siebel.models import SiebelSubscription
from apps.paywall.classes.history_state import HistoryState
from apps.paywall.classes.subscription_syncing_facebook import SubscriptionSyncingFacebook
from apps.paywall.shortcuts import render_send_email


class ApiSubscriptionFailRenewView(APIView):

    def post(self, request):
        """
            Procesa los eventos FAIL_RENEW_SUBSCRIPTION, TERMINATE_SUBSCRIPTION

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

        subscription, created_sub = Subscription.objects.get_or_create_subs(
            site=params['site'],
            subscription_id=params['subscription'],
            sync_data=True,
        )
        history_state = HistoryState(subscription)
        history_state.update_data()

        evento = Event.objects.get(
            index=params['event_index'],
        )

        if params['event'] == 'FAIL_RENEW_SUBSCRIPTION':
            fail_renew_subscription, created = FailRenewSubscription.objects.get_or_create(
                subscription=subscription,
                event=evento,
                event_type=params['event']
            )
            if created:
                self.send_mail_fail_renew_subscription(subscription)

        elif params['event'] == 'TERMINATE_SUBSCRIPTION':
            # -------------------habilitar para FIA -------------------------------------------------
            # subscription_syncing_facebook = SubscriptionSyncingFacebook(subscription, params['site'])
            # subscription_syncing_facebook.update_data()

            _, created = FailRenewSubscription.objects.get_or_create(
                subscription=subscription,
                event=evento,
                event_type=params['event']
            )

            if created:
                self.send_mail_terminate_subscription(subscription)

            # Desactiva la suscripcion club
            if subscription.by_payu_method():
                ClubSubscription.objects.deactivate_subscriptions(
                    subscription=subscription
                )

            # Inicia la baja por lógica de Siebel
            """
            if subscription.get_siebel_delivery():
                try:
                    UnsubscribeClient().siebel_suspend(subscription)
                except Exception:
                    capture_exception()
            """
            # Agrega el tipo de baja de la suscripcion
            if subscription.by_payu_method():
                try:
                    self.add_type_low(subscription)
                except Exception:
                    capture_exception()

            # Agrega los tipos de suspenciones de la baja
            if subscription.by_payu_method():
                try:
                    self.add_low_by_suspencion(subscription)
                except Exception:
                    capture_exception()

        elif params['event'] == 'SUSPEND_SUBSCRIPTION':
            fail_renew_subscription, _ = FailRenewSubscription.objects.get_or_create(
                subscription=subscription,
                event=evento,
                event_type=params['event']
            )

        return Response(
            status=status.HTTP_200_OK
        )

    def add_low_by_suspencion(self, subscription):
        if not LowBySuspension.objects.filter(subscription=subscription).exists():
            try:
                events = subscription.data.get('events', '')
            except Exception:
                events = ''

            if events:
                ordered_events = sorted(events, key=lambda i: i['eventDateUTC'])
                total = len(ordered_events) - 1
                penultimate_event = ordered_events[total - 1]
                if penultimate_event:
                    if 'FAIL_RENEW_SUBSCRIPTION' in penultimate_event.get('eventType', ''):
                        event_content = penultimate_event.get('details', '')
                        event_content_list = event_content.split("-")
                        try:
                            name_event = event_content_list[0]
                        except Exception:
                            name_event = ''

                        try:
                            detail_event = event_content_list[1]
                        except Exception:
                            detail_event = ''

                        if not EventTypeSuspension.objects.filter(name=name_event).exists():
                            event_type = EventTypeSuspension(
                                name=name_event
                            )
                            event_type.save()

                        low_by_suspension = LowBySuspension(
                            subscription=subscription,
                            event_type=name_event,
                            detail=detail_event
                        )
                        low_by_suspension.save()

    def add_type_low(self, subscription):
        if not TypeOfLowSubscription.objects.filter(subscription=subscription).exists():
            try:
                events = subscription.data.get('events', '')
            except Exception:
                events = ''

            if events:
                ordered_events = sorted(events, key=lambda i: i['eventDateUTC'])
                total = len(ordered_events) - 1
                penultimate_event = ordered_events[total - 1]
                if penultimate_event:
                    list_suspend = ['SUSPEND_SUBSCRIPTION', 'FAIL_RENEW_SUBSCRIPTION']

                    if penultimate_event.get('eventType', '') in list_suspend:
                        type_of_low = TypeOfLowSubscription(
                            subscription=subscription,
                            type=TypeOfLowSubscription.LOW_BY_SUSPENSION
                        )
                        type_of_low.save()

                    elif penultimate_event.get('eventType', '') == 'CANCEL_SUBSCRIPTION':
                        type_of_low = TypeOfLowSubscription(
                            subscription=subscription,
                            type=TypeOfLowSubscription.LOW_BY_CANCELLATION
                        )
                        type_of_low.save()

                    elif penultimate_event.get('eventType', '') in \
                            ['START_SUBSCRIPTION', 'RENEW_SUBSCRIPTION', 'UPDATE_PAYMENT_METHOD']:
                        type_of_low = TypeOfLowSubscription(
                            subscription=subscription,
                            type=TypeOfLowSubscription.LOW_BY_ADMIN
                        )
                        type_of_low.save()
                    else:
                        capture_event(
                            {
                                'message': 'Tipo de baja no detectado',
                                'extra': {
                                    'suscripcion': subscription,
                                }
                            }
                        )

    def send_mail_terminate_subscription(self, subscription):
        no_envia = 1
        partner = subscription.partner
        plan = subscription.plan

        payment_partner = subscription.data['currentPaymentMethod']['paymentPartner']
        if payment_partner != 'Free' and payment_partner != 'Linked':
            card_number = '**** **** **** {}'.format(
                subscription.data['currentPaymentMethod']['lastFour']
            )
        else:
            card_number = ''

        setting_legal = {
            'terms': partner.terms_of_service_url,
            'policies_privacy': partner.privacy_policy_url,
            'frequent_questions': partner.faq_url
        }

        product_name = '{} - {}'.format(
            plan.product.prod_name, plan.get_frequency_name()
        )

        email = subscription.get_email()

        data = {
            'card_number': card_number,
            'legal': setting_legal,
            'product': product_name,
            'rate_description': plan.get_rate_description(),
            'site': partner.partner_code,
            'site_name': partner.partner_name,
            'url_base': settings.PAYWALL_MAILING_ASSETS_URL,
            'us_email': email,
            'us_fullname': subscription.get_full_name()
        }

        data_subscription = SalesClient().get_subscription(
            site=partner.partner_code,
            subscription_id=subscription.arc_id
        )
        if data_subscription.get('events', '')[-2].get('eventType', '') == 'CANCEL_SUBSCRIPTION':
            template_name = 'mailings/%s/subscription_finalice_subscription.html' % partner.partner_code
        elif data_subscription.get('events', '')[-2].get('eventType', '') in ['START_SUBSCRIPTION', 'RENEW_SUBSCRIPTION']:
            no_envia = 0
        else:
            template_name = 'mailings/%s/subscription_terminate.html' % partner.partner_code

        subject = '[%s] Termino de tu suscripción - %s' % (partner.partner_name, plan.product.prod_name)
        from_email = '{name_sender} <{direction_sender}>'.format(
            name_sender=partner.partner_name,
            direction_sender=partner.transactional_sender
        )

        if no_envia:
            render_send_email(
                template_name=template_name,
                subject=subject,
                to_emails=email,
                from_email=from_email,
                context=data,
            )

    def send_mail_fail_renew_subscription(self, subscription):
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
        if partner.nro_renewal_attempts:
            count = 0

            data_subscription = SalesClient().get_subscription(
                site=partner.partner_code,
                subscription_id=subscription.arc_id
            )
            for event in data_subscription['events'][::-1]:
                if event['eventType'] == 'START_SUBSCRIPTION' or event['eventType'] == 'RENEW_SUBSCRIPTION' \
                        or event['eventType'] == 'TERMINATE_SUBSCRIPTION':
                    break

                if event['eventType'] == 'FAIL_RENEW_SUBSCRIPTION':
                    count = count + 1

            if count:
                number_renewal_attempts = int(partner.nro_renewal_attempts) - count
            else:
                number_renewal_attempts = 0
        else:
            number_renewal_attempts = 0

        data = {
            'card_number': card_number,
            'legal': setting_legal,
            'product': product_name,
            'rate_description': plan.get_rate_description(),
            'site': partner.partner_code,
            'site_name': partner.partner_name,
            'url_base': settings.PAYWALL_MAILING_ASSETS_URL,
            'us_email': email,
            'us_fullname': subscription.get_full_name(),
            'number_renewal_attempts': number_renewal_attempts
        }

        template_name = 'mailings/%s/insufficient_funds.html' % partner.partner_code
        subject = '[%s] Error en el cobro de tu suscripción - %s' % (partner.partner_name, plan.product.prod_name)
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
