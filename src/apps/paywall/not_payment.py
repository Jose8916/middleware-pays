from datetime import datetime, timedelta, date
from django.db.models.aggregates import Max
from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.utils.timezone import get_default_timezone
from django.views import View

from .forms import RangeDateForm
from .models import Plan, Subscription, Payment, SubscriptionState
from sentry_sdk import capture_message, capture_exception, capture_event


class NoPaymentReportView(View):
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
        start_date_begin = "2019-01-01"
        start_date_begin = datetime.strptime(start_date_begin, '%Y-%m-%d')
        start_date_begin = self.start_day(start_date_begin)
        #
        # end_date = "2020-01-31"
        # end_date = datetime.strptime(end_date, '%Y-%m-%d')
        # end_date = self.end_day(end_date)

        form = RangeDateForm(request.POST or None)
        if form.is_valid():
            start_date = self.start_day(form.cleaned_data.get('start_date'))
            end_date = self.end_day(form.cleaned_data.get('end_date'))

            subscription_states = SubscriptionState.objects.filter(
                state=SubscriptionState.ARC_STATE_SUSPENDED,
                date__range=self.range_to_timestamp(start_date, end_date)
            )
            list_subscriptions = []
            for subs_state in subscription_states:
                subscription_states = SubscriptionState.objects.filter(
                    subscription=subs_state.subscription,
                    date__range=self.range_to_timestamp(start_date, end_date),
                    event_type='RENEW_SUBSCRIPTION').count()
                if not subscription_states:
                    list_subscriptions.append(subs_state.subscription)

            list_payments = []
            for subs in list_subscriptions:
                try:
                    payment = Payment.objects.filter(
                        date_payment__range=self.range_to_timestamp(start_date_begin, end_date)
                    ).filter(subscription=subs).order_by('-date_payment')[0]
                except Exception as e:
                    payment = ''

                if payment:
                    list_payments.append(payment)

            context = {
                'payment': list_payments,
            }

            template = loader.get_template('admin/report/suspended_payment.html')
            return HttpResponse(template.render(context, request))
