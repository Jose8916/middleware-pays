from datetime import datetime, timedelta, date
from django.db.models.aggregates import Max
from django.http import HttpResponse
from django.template import loader
from django.utils.timezone import get_default_timezone
from django.views import View

from .forms import RangeDateForm
from .models import Plan, Subscription, Payment, SubscriptionState
from sentry_sdk import capture_message, capture_exception, capture_event


class NoPaymentJanuaryReportView(View):
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

    def get(self, request, *args, **kwargs):
        context = {
            'form': RangeDateForm,
        }
        template = loader.get_template('admin/report/suspended_payment.html')
        return HttpResponse(template.render(context, request))

    def post(self, request, *args, **kwargs):
        # start_date = "2020-01-01"
        # start_date = datetime.strptime(start_date, '%Y-%m-%d')
        # start_date = self.start_day(start_date)
        #
        # end_date = "2020-01-31"
        # end_date = datetime.strptime(end_date, '%Y-%m-%d')
        # end_date = self.end_day(end_date)

        form = RangeDateForm(request.POST or None)
        if form.is_valid():
            today_day = self.end_day(date.today())
            start_date = self.start_day(form.cleaned_data.get('start_date'))
            end_date = self.end_day(form.cleaned_data.get('end_date'))

            subscription_states = SubscriptionState.objects.filter(
                state=SubscriptionState.ARC_STATE_SUSPENDED,
                date__range=self.range_to_timestamp(start_date, end_date),
            )
            list_subscriptions = []
            for obj_subs_state in subscription_states:
                date_obj = obj_subs_state.date
                try:
                    value = SubscriptionState.objects.filter(date__range=self.range_to_timestamp(date_obj, today_day),
                                                             subscription=obj_subs_state.subscription).exclude(state=SubscriptionState.ARC_STATE_ACTIVE)
                except Exception as e:
                    value = ''

                if value:
                    list_subscriptions.append(obj_subs_state.subscription)


            # for obj_subs_state in subscription_states:
            #     orden_subscriptions = SubscriptionState.objects.filter(subscription=obj_subs_state.subscription).order_by('date')
            #     for obj_subs in orden_subscriptions:
            #         if flag:
            #
            #         if obj_subs.id == obj_subs_state.id:
            #             flag = obj_subs.id
            #
            #
            #
            #
            # next_id_subscription = (subscription_state.id)+ 1
            # validate_sub=SubscriptionState.objects.get(id=next_id_subscription)
            # if validate_sub.state != 'renew':
            #     append(subscripition
            #
            #            )

            # filtrar que las siguientes state subscription sean diferentes a renew

            list_payments = []
            for subs in list_subscriptions:
                try:
                    payment = Payment.objects.filter(subscription=subs).order_by('-date_payment')[0]
                except Exception as e:
                    payment = ''

                if payment:
                    list_payments.append(payment)

            # # subscription_state = subscription_state.exclude(
            # #     event_type='RENEW_SUBSCRIPTION'
            # # )
            #
            # list_subscripitions = []
            # for s in subscription_state:
            #     list_subscripitions.append(s.subscription)
            #
            # last_payments = Payment.objects.filter(subscription__in=list_subscripitions) \
            #     .values('id') \
            #     .annotate(max_date=Max('date_payment'))
            #
            # list_id_payments = []
            # for pay in last_payments:
            #     list_id_payments.append(pay.get('id'))
            #
            # return HttpResponse(list_id_payments)
            # payment = Payment.objects.filter(
            #     id__in=list_id_payments,
            # ).exclude(subscription__state=Subscription.ARC_STATE_ACTIVE)

            context = {
                'payment': list_payments,
            }

            template = loader.get_template('admin/report/suspended_payment.html')
            return HttpResponse(template.render(context, request))


class PaymentNotChargedReportView(View):
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

    def get(self, request, *args, **kwargs):
        context = {
            'form': RangeDateForm,
        }
        template = loader.get_template('admin/report/suspended_payment.html')
        return HttpResponse(template.render(context, request))

    def post(self, request, *args, **kwargs):
        # start_date = "2020-01-01"
        # start_date = datetime.strptime(start_date, '%Y-%m-%d')
        # start_date = self.start_day(start_date)
        #
        # end_date = "2020-01-31"
        # end_date = datetime.strptime(end_date, '%Y-%m-%d')
        # end_date = self.end_day(end_date)

        form = RangeDateForm(request.POST or None)
        if form.is_valid():

            start_date = self.start_day(form.cleaned_data.get('start_date'))
            end_date = self.end_day(form.cleaned_data.get('end_date'))

            subscription_state = SubscriptionState.objects.filter(
                state=SubscriptionState.ARC_STATE_SUSPENDED,
                date__range=self.range_to_timestamp(start_date, end_date),
            )

            subscription_state = subscription_state.exclude(
                event_type='RENEW_SUBSCRIPTION'
            )

            list_subscripitions = []
            for s in subscription_state:
                list_subscripitions.append(s.subscription)

            payment = Payment.objects.filter(
                transaction_date__range=self.range_to_timestamp(start_date, end_date),
                subscription__in=list_subscripitions,
            )
            # date = self.range_to_timestamp(start_date, end_date)

            # subscription_state = subscription_state.subscription

            context = {
                'payment': payment,
            }

            template = loader.get_template('admin/report/suspended_payment.html')
            return HttpResponse(template.render(context, request))
