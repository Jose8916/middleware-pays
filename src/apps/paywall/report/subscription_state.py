from datetime import datetime

from django.http import HttpResponse
from django.template import loader
from django.views import View
from django.utils.timezone import get_default_timezone

from ..models import Subscription, SubscriptionState

from apps.paywall.arc_clients import SalesClient
from apps.arcsubs.utils import timestamp_to_datetime
from apps.paywall.forms import RangeDateForm


class SuscriptionStateReportView(View):
    def get(self, request, *args, **kwargs):
        template = loader.get_template('admin/report/renovations.html')
        context = {
            'form': RangeDateForm,
            'fail_renew_subscriptions': '',
            'sites': '',
            'total': 0
        }
        return HttpResponse(template.render(context, request))

    def post(self, request, *args, **kwargs):
        list_fail_renew = []
        form = RangeDateForm(request.POST or None)

        if form.is_valid():
            start_date = self.start_day(form.cleaned_data.get('start_date'))
            end_date = self.end_day(form.cleaned_data.get('end_date'))

        list_subscriptions = self.get_data_subscription(request, start_date, end_date)
        data_subscriptions = Subscription.objects.filter(arc_id__in=list_subscriptions)
        for subscription in data_subscriptions:
            if subscription.payment_profile:
                name_user = subscription.payment_profile.get_full_name()
            else:
                name_user = ""

            try:
                data_subscription = SalesClient().get_subscription(
                    site=subscription.partner.partner_code,
                    subscription_id=subscription.arc_id
                )
            except Exception:
                data_subscription = ''

            try:
                detail = data_subscription.get('events', '')
            except Exception:
                detail = ''

            final_payment = self.get_final_payment(data_subscription)

            dict_fail_renew = {
                'nombre_suscripcion': self.get_plan_name(subscription),
                'brand': self.get_partner_code(subscription),
                'code_subscription': subscription.arc_id,
                'email': self.get_portal_email(subscription),
                'name_user': name_user,
                'cantidad_intentos': '',  # self.get_countattempts(data),
                'detail': '',  # detail_fail,
                'date_start': subscription.starts_date,
                'date_renovation': self.get_period_to(final_payment),
                'date_terminate': subscription.date_anulled,
                'detail_all': detail,
                'estado': subscription.state
            }
            list_fail_renew.append(dict_fail_renew)

        template = loader.get_template('admin/report/renovations.html')
        context = {
            'form': form,
            'estado': request.POST.get('estado', ''),
            'site': request.POST.get('site', ''),
            'fail_renew_subscriptions': list_fail_renew,
            'sites': '',
            'total': len(list_fail_renew)
        }
        return HttpResponse(template.render(context, request))

    def get_period_to(self, subscription):
        try:
            return timestamp_to_datetime(subscription['periodTo'])
        except Exception:
            return ''

    def range_to_timestamp(self, start_date, end_date):
        starts = datetime.combine(
            start_date,
            datetime.min.time()
        )
        ends = datetime.combine(
            end_date,
            datetime.max.time()
        )
        return (
            get_default_timezone().localize(starts),
            get_default_timezone().localize(ends)
        )

    def get_data_subscription(self, request, start_date, end_date):
        estado = request.POST.get('estado', '')
        site = request.POST.get('site', '')
        include_list = []

        if estado == 'terminados_cancelados':
            data_subscriptions = SubscriptionState.objects.filter(
                state=SubscriptionState.ARC_STATE_TERMINATED,
                date__range=self.range_to_timestamp(start_date, end_date)
            )
            if site:
                data_subscriptions = data_subscriptions.filter(subscription__partner__partner_code=site)

            for subscription_obj in data_subscriptions:
                subscription_state = SubscriptionState.objects.filter(
                    subscription=subscription_obj.subscription
                ).order_by('date')

                list_state = []

                for state_obj in subscription_state:
                    list_state.append(state_obj.state)

                if list_state[-2] == SubscriptionState.ARC_STATE_CANCELED:
                    include_list.append(subscription_obj.subscription.arc_id)

        elif estado == 'terminados_suspendidos':
            data_subscriptions = SubscriptionState.objects.filter(
                state=SubscriptionState.ARC_STATE_TERMINATED,
                date__range=self.range_to_timestamp(start_date, end_date)
            )
            if site:
                data_subscriptions = data_subscriptions.filter(subscription__partner__partner_code=site)

            for subscription_obj in data_subscriptions:
                subscription_state = SubscriptionState.objects.filter(
                    subscription=subscription_obj.subscription
                ).order_by('date')

                list_state = []

                for state_obj in subscription_state:
                    list_state.append(state_obj.state)

                if list_state[-2] == SubscriptionState.ARC_STATE_SUSPENDED:
                    include_list.append(subscription_obj.subscription.arc_id)

        elif estado == 'terminated_by_arc_admin':
            data_subscriptions = SubscriptionState.objects.filter(
                state=SubscriptionState.ARC_STATE_TERMINATED,
                date__range=self.range_to_timestamp(start_date, end_date)
            )
            if site:
                data_subscriptions = data_subscriptions.filter(subscription__partner__partner_code=site)

            for subscription_obj in data_subscriptions:
                subscription_state = SubscriptionState.objects.filter(
                    subscription=subscription_obj.subscription
                ).order_by('date')

                list_state = []

                for state_obj in subscription_state:
                    list_state.append(state_obj.state)

                if list_state[-2] == SubscriptionState.ARC_STATE_ACTIVE:
                    include_list.append(subscription_obj.subscription.arc_id)

        return include_list

    def get_plan_name(self, subscription):
        try:
            return subscription.plan.plan_name
        except Exception:
            return ''

    def get_portal_email(self, subscription):
        try:
            return subscription.payment_profile.portal_email
        except Exception:
            return ''

    def get_final_payment(self, subscription):
        try:
            return  subscription.get('paymentHistory')[-1]
        except Exception:
            return ''

    def get_partner_code(self, subscription):
        try:
            return subscription.partner.partner_code
        except Exception:
            return ''

    def start_day(self, start_date):
        starts = datetime.combine(
            start_date,
            datetime.min.time()
        )
        return get_default_timezone().localize(starts)

    def end_day(self, end_date):
        ends = datetime.combine(
            end_date,
            datetime.max.time()
        )
        return get_default_timezone().localize(ends)
