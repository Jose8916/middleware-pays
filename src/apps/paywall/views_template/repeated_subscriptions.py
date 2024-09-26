from django.db.models import Count
from datetime import datetime, timedelta
from django.http import HttpResponse
from django.template import loader
from django.utils.timezone import get_default_timezone
from django.views import View

from apps.paywall.functions.utils_report import get_subscription_data, get_info_payment, get_payments, get_refund, \
    get_info_login_user
from apps.paywall.forms import RangeDateForm
from apps.paywall.models import Operation, Plan, Subscription, Product, Payment, ArcUser


class SubscriptionDoubleReport(View):
    """
        Cantidad de suscripciones repetidas
    """

    def get(self, request, *args, **kwargs):
        template = loader.get_template('admin/report/double_subscriptions.html')

        context = {
            'form': RangeDateForm,
            'lists_users': [],
        }
        return HttpResponse(template.render(context, request))

    def post(self, request, *args, **kwargs):
        template = loader.get_template('admin/report/double_subscriptions.html')
        form = RangeDateForm(request.POST or None)

        if form.is_valid():
            start_date = self.start_day(form.cleaned_data.get('start_date'))
            end_date = self.end_day(form.cleaned_data.get('end_date'))

            subscriptions = Subscription.objects.values(
                'arc_user__uuid', 'plan',
            ).annotate(
                plan_count=Count('plan')
            ).filter(
                plan_count__gt=1,
                starts_date__range=self.range_to_timestamp(start_date, end_date)
            )

            lists_users = []

            for obj_list in subscriptions:
                plan_obj = Plan.objects.get(id=obj_list.get('plan'))
                arc_user = ArcUser.objects.get(uuid=obj_list.get('arc_user__uuid'))
                filter_subscription = Subscription.objects.filter(
                    arc_user=arc_user,
                    plan=plan_obj,
                    starts_date__range=self.range_to_timestamp(start_date, end_date)
                )
                list_subscription = []
                for obj_subscription in filter_subscription:
                    list_subscription.append(
                        {
                            'subscription': get_subscription_data(obj_subscription),
                            'info_payment': get_info_payment(obj_subscription),
                            'refund_list': get_refund(obj_subscription),
                            'detail_payment': get_payments(obj_subscription)
                        }
                    )

                obj_list['plan_name'] = plan_obj.plan_name
                obj_list['subscriptions'] = list_subscription
                obj_list['user_login'] = get_info_login_user(arc_user) if arc_user else '-'
                lists_users.append(obj_list)

            context = {
                'form': form,
                'lists_users': lists_users,
            }
            return HttpResponse(template.render(context, request))

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