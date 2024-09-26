from django.http import HttpResponse
from django.template import loader
from django.views import View

from .models import FailRenewSubscription, Subscription
from apps.arcsubs.models import Event
from apps.paywall.arc_clients import SalesClient
from ..arcsubs.utils import timestamp_to_datetime


class RenewalReportView(View):
    def get(self, request, *args, **kwargs):
        template = loader.get_template('admin/report/renovations.html')
        context = {
            'fail_renew_subscriptions': '',
            'sites': '',
            'total': 0
        }
        return HttpResponse(template.render(context, request))

        query_string = """
            SELECT
                1 as id , subscription_id, COUNT(subscription_id) as count_attempts
            FROM
                paywall_failrenewsubscription
            WHERE
                event_type=\'FAIL_RENEW_SUBSCRIPTION\'
            GROUP BY (subscription_id);"""
        fail_renew_subscriptions = FailRenewSubscription.objects.raw(query_string)

        # fail_renew_subscriptions = FailRenewSubscription.objects.values('subscription_id').\
        #     annotate(count_attempts=Count('subscription_id')).filter(event_type='FAIL_RENEW_SUBSCRIPTION')
        list_fail_renew = []
        for data in fail_renew_subscriptions:
            subscription = Subscription.objects.get(id=data.subscription_id)

            if subscription.payment_profile:
                if subscription.payment_profile.prof_name and subscription.payment_profile.prof_lastname \
                        and subscription.payment_profile.prof_lastname_mother:
                    name_user = "{name} {last_name} {lastname_mother}".format(
                        name=subscription.payment_profile.prof_name,
                        last_name=subscription.payment_profile.prof_lastname,
                        lastname_mother=subscription.payment_profile.prof_lastname_mother)
                elif subscription.payment_profile.prof_name and subscription.payment_profile.prof_lastname:
                    name_user = "{name} {last_name}".format(name=subscription.payment_profile.prof_name,
                                                            last_name=subscription.payment_profile.prof_lastname)
                else:
                    name_user = ""
            else:
                name_user = ""
            try:
                plan_name = subscription.plan.plan_name
            except Exception:
                plan_name = ''

            try:
                email_user = subscription.payment_profile.portal_email
            except Exception:
                email_user = ''

            data_subscription = SalesClient().get_subscription(
                site=subscription.partner.partner_code,
                subscription_id=subscription.arc_id
            )
            final_payment = data_subscription.get('paymentHistory')[-1]
            period_to = timestamp_to_datetime(final_payment['periodTo'])

            detail = data_subscription.get('events', '')
            detail_fail = ''
            fecha_terminate = ''
            for obj_detail in detail:
                if obj_detail.get('eventType', '') == 'START_SUBSCRIPTION':
                    date_start = timestamp_to_datetime(obj_detail.get('eventDateUTC', ''))

                if obj_detail.get('eventType', '') == 'FAIL_RENEW_SUBSCRIPTION' and not detail_fail:
                    detail_fail = obj_detail.get('details', '')

                if obj_detail.get('eventType', '') == 'TERMINATE_SUBSCRIPTION':
                    fecha_terminate = timestamp_to_datetime(obj_detail.get('eventDateUTC', ''))
                    break

            dict_fail_renew = {
                'nombre_suscripcion': plan_name,
                'brand': subscription.partner.partner_code,
                'code_subscription': subscription.arc_id,
                'email': email_user,
                'name_user': name_user,
                'cantidad_intentos': data.count_attempts,
                'detail': detail_fail,
                'date_start': date_start,
                'date_renovation': period_to,
                'date_terminate': fecha_terminate,
                'detail_all': detail
            }
            list_fail_renew.append(dict_fail_renew)

        template = loader.get_template('admin/report/renovations.html')
        context = {
            'fail_renew_subscriptions': list_fail_renew,
            'sites': '',
            'total': len(list_fail_renew)
        }
        return HttpResponse(template.render(context, request))

    def post(self, request, *args, **kwargs):
        # suscripciones = Subscription.objects.filter(data__events__contains=[{"eventType": "CANCEL_SUBSCRIPTION"}])
        # return HttpResponse(suscripciones)
        # dict_fail_renew = {
        #     'nombre_suscripcion': suscripcion.plan.plan_name,
        #     'brand': suscripcion.partner.partner_code,
        #     'code_subscription': suscripcion.arc_id,
        #     'email': self.email_user(suscripcion),
        #     'name_user': self.name_user(suscripcion),
        #     'cantidad_intentos': '',
        #     'detail': '',
        #     'date_start': self.date_start(suscripcion),
        #     'date_renovation': self.period_to(suscripcion),
        #     'date_terminate': self.fecha_terminate(suscripcion),
        #     'detail_all': '',
        #     'estado': estado
        # }

        estado = request.POST.get('estado', '')
        if estado == 'cancelados' or estado == 'terminados_cancelados':
            query_string = """
                                SELECT  1 as id , message->>'subscriptionID' as subscription_id
                                FROM arcsubs_event
                                WHERE event_type = \'CANCEL_SUBSCRIPTION\'
                                GROUP BY (subscription_id)"""
            data_subscriptions = Event.objects.raw(query_string)
        elif estado == 'suspendidos' or estado == 'terminados_suspendidos':
            query_string = """
                SELECT  1 as id , subscription_id, COUNT(subscription_id) as count_attempts
                FROM paywall_failrenewsubscription
                WHERE event_type=\'FAIL_RENEW_SUBSCRIPTION\'
                GROUP BY (subscription_id)"""
            data_subscriptions = FailRenewSubscription.objects.raw(query_string)

        # fail_renew_subscriptions = FailRenewSubscription.objects.values('subscription_id').\
        #     annotate(count_attempts=Count('subscription_id')).filter(event_type='FAIL_RENEW_SUBSCRIPTION')
        list_fail_renew = []

        for data in data_subscriptions:
            if estado == 'terminados_suspendidos':
                cantidad = FailRenewSubscription.objects.filter(subscription_id=data.subscription_id,
                                                                event_type='TERMINATE_SUBSCRIPTION').count()
                if cantidad > 0:
                    cantidad = 1
                else:
                    cantidad = 0
            if estado == 'terminados_cancelados':
                cantidad = Subscription.objects.filter(arc_id=data.subscription_id, state=2).count()
                if cantidad > 0:
                    cantidad = 1
                else:
                    cantidad = 0
            if estado == 'suspendidos':
                cantidad = FailRenewSubscription.objects.filter(subscription_id=data.subscription_id,
                                                                event_type='TERMINATE_SUBSCRIPTION').count()
                if cantidad > 0:
                    cantidad = 0
                else:
                    cantidad = 1
            if estado == 'cancelados':
                cantidad = Subscription.objects.filter(arc_id=data.subscription_id, state=2).count()
                if cantidad > 0:
                    cantidad = 0
                else:
                    cantidad = 1

            if cantidad:
                if estado == 'cancelados' or estado == 'terminados_cancelados':
                    subscription = Subscription.objects.get(arc_id=data.subscription_id)
                else:
                    subscription = Subscription.objects.get(id=data.subscription_id)

                if subscription.payment_profile:
                    if subscription.payment_profile.prof_name and subscription.payment_profile.prof_lastname \
                            and subscription.payment_profile.prof_lastname_mother:
                        name_user = "{name} {last_name} {lastname_mother}".format(
                            name=subscription.payment_profile.prof_name,
                            last_name=subscription.payment_profile.prof_lastname,
                            lastname_mother=subscription.payment_profile.prof_lastname_mother)
                    elif subscription.payment_profile.prof_name and subscription.payment_profile.prof_lastname:
                        name_user = "{name} {last_name}".format(name=subscription.payment_profile.prof_name,
                                                                last_name=subscription.payment_profile.prof_lastname)
                    else:
                        name_user = ""
                else:
                    name_user = ""

                try:
                    plan_name = subscription.plan.plan_name
                except Exception:
                    plan_name = ''

                try:
                    email_user = subscription.payment_profile.portal_email
                except Exception:
                    email_user = ''

                try:
                    data_subscription = SalesClient().get_subscription(
                        site=subscription.partner.partner_code,
                        subscription_id=subscription.arc_id
                    )
                except Exception:
                    data_subscription = ''

                final_payment = self.get_final_payment(data_subscription)


                try:
                    detail = data_subscription.get('events', '')
                except Exception:
                    detail = ''

                detail_fail = ''
                fecha_terminate = ''
                for obj_detail in detail:
                    if obj_detail.get('eventType', '') == 'START_SUBSCRIPTION':
                        date_start = timestamp_to_datetime(obj_detail.get('eventDateUTC', ''))

                    if obj_detail.get('eventType', '') == 'FAIL_RENEW_SUBSCRIPTION' and not detail_fail:
                        detail_fail = obj_detail.get('details', '')

                    if obj_detail.get('eventType', '') == 'TERMINATE_SUBSCRIPTION':
                        fecha_terminate = timestamp_to_datetime(obj_detail.get('eventDateUTC', ''))
                        break

                dict_fail_renew = {
                    'nombre_suscripcion': plan_name,
                    'brand': self.get_partner_code(subscription),
                    'code_subscription': subscription.arc_id,
                    'email': email_user,
                    'name_user': name_user,
                    'cantidad_intentos': self.get_countattempts(data),
                    'detail': detail_fail,
                    'date_start': date_start,
                    'date_renovation': self.get_period_to(final_payment),
                    'date_terminate': fecha_terminate,
                    'detail_all': detail,
                    'estado': estado
                }
                list_fail_renew.append(dict_fail_renew)

        template = loader.get_template('admin/report/renovations.html')
        context = {
            'estado': estado,
            'fail_renew_subscriptions': list_fail_renew,
            'sites': '',
            'total': len(list_fail_renew)
        }

        return HttpResponse(template.render(context, request))

    def get_partner_code(self, subscription):
        try:
            return subscription.partner.partner_code
        except Exception:
            return ''

    def get_final_payment(self, subscription):
        try:
            return  subscription.get('paymentHistory')[-1]
        except Exception:
            return ''

    def get_countattempts(self, subscription):
        try:
            return subscription.count_attempts
        except Exception:
            return ''

    def email_user(self, subscription):
        try:
            return subscription.payment_profile.portal_email
        except Exception:
            return ''

    def name_user(self, subscription):
        if subscription.payment_profile:
            if subscription.payment_profile.prof_name and subscription.payment_profile.prof_lastname \
                    and subscription.payment_profile.prof_lastname_mother:
                name_user = "{name} {last_name} {lastname_mother}".format(
                    name=subscription.payment_profile.prof_name,
                    last_name=subscription.payment_profile.prof_lastname,
                    lastname_mother=subscription.payment_profile.prof_lastname_mother)
            elif subscription.payment_profile.prof_name and subscription.payment_profile.prof_lastname:
                name_user = "{name} {last_name}".format(name=subscription.payment_profile.prof_name,
                                                        last_name=subscription.payment_profile.prof_lastname)
            else:
                name_user = ""
        else:
            name_user = ""
        return name_user

    def date_start(self, subscription):
        detail = subscription.data.get('events', '')
        date_start = ''
        for obj_detail in detail:
            if obj_detail.get('eventType', '') == 'START_SUBSCRIPTION':
                date_start = timestamp_to_datetime(obj_detail.get('eventDateUTC', ''))
                break
        return date_start

    def get_period_to(self, subscription):
        try:
            return timestamp_to_datetime(subscription['periodTo'])
        except Exception:
            return ''

    def fecha_terminate(self, subscription):
        detail = subscription.data.get('events', '')

        fecha_terminate = ''
        for obj_detail in detail:
            if obj_detail.get('eventType', '') == 'TERMINATE_SUBSCRIPTION':
                fecha_terminate = timestamp_to_datetime(obj_detail.get('eventDateUTC', ''))
        return fecha_terminate