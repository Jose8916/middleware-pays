from datetime import datetime, timedelta

from django.conf import settings
from django.utils.html import format_html
from django.http import HttpResponse
from django.template import loader
from django.utils.timezone import get_default_timezone
from django.utils import formats, timezone
from django.views import View

from .forms import RangeDateForm
from .models import Operation, Plan, Subscription, Product, Payment, ReportLongPeriodTime
from apps.arcsubs.utils import timestamp_to_datetime
from sentry_sdk import capture_exception


class SalesReportView(View):
    def get(self, request, *args, **kwargs):
        template = loader.get_template('admin/report/sales_report.html')
        context = {
            'form': RangeDateForm,
            'sites': ''
        }
        return HttpResponse(template.render(context, request))

    def table_headers(self):
        table_headers = []
        list_plan = []
        products = Product.objects.filter(state=True)

        for product in products:
            plans = Plan.objects.filter(product=product, state=True)
            for plan in plans:
                if plan.arc_pricecode:
                    list_plan.append(
                        {
                            'name': plan.plan_name,
                            'arc_pricecode': plan.arc_pricecode
                        }
                    )
            if product.partner.partner_code == 'gestion':
                color = 'FF7733'
            else:
                color = 'yellow'

            table_headers.append(
                {
                    'name_product': product.prod_name + ' - ' + product.partner.partner_name,
                    'arc_sku': product.arc_sku,
                    'planes': list_plan,
                    'color_brand': color
                }
            )
        return table_headers

    def post(self, request, *args, **kwargs):
        form = RangeDateForm(request.POST or None)
        table_data = []

        if form.is_valid():
            start_date = self.start_day(form.cleaned_data.get('start_date'))
            end_date = self.end_day(form.cleaned_data.get('end_date'))
            total_subscriptions = self.get_queryset_base(start_date, end_date)
            total_payments = self.get_payment_base(start_date, end_date)
            range_date_search = end_date - start_date

            table_headers = self.table_headers()

            for count in range(range_date_search.days + 1):
                day = start_date + timedelta(days=count)
                queryset_base = self.get_queryset_base(day, day)
                query_payment = self.get_payment_base(day, day)
                queries = self.get_row_data(day, queryset_base, table_headers, query_payment)
                table_data.append(queries)
                table_footer = self.get_row_totales(total_subscriptions, total_payments, table_headers)

        sum_altas = 0
        sum_pagos = 0
        for footer in table_footer:
            sum_altas = sum_altas + int(footer.get('altas_total', ''))
            sum_pagos = sum_pagos + int(footer.get('pagos_total', ''))

        context = {
            'form': form,
            'table_data': table_data,
            'table_headers': table_headers,
            'table_footer': table_footer,
            'total_altas': sum_altas,
            'total_cobros': sum_pagos
        }
        template = loader.get_template('admin/report/sales_report.html')
        return HttpResponse(template.render(context, request))

    def get_queryset_base(self, start_date, end_date):
        # domain = form.cleaned_data.get('domain')
        # device = form.cleaned_data.get('device')
        # action = form.cleaned_data.get('origin_action')

        queryset = Subscription.objects.filter(
            created__range=self.range_to_timestamp(start_date, end_date)
        )
        return queryset

    def get_payment_base(self, start_date, end_date):
        payment = Payment.objects.filter(
            created__range=self.range_to_timestamp(start_date, end_date)
        )
        return payment

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

    def get_row_totales(self, query, query_payment, table_headers):

        producto = []
        for table_obj in table_headers:
            product_query = query.filter(plan__product__arc_sku=table_obj.get('arc_sku'))
            payment_query = query_payment.filter(subscription__plan__product__arc_sku=table_obj.get('arc_sku'))

            producto.append(
                {
                    'altas_total': product_query.count(),
                    'pagos_total': payment_query.count()
                }
            )

        return producto

    def get_row_data(self, day, query, table_headers, query_payment):
        row = {
            'day': day,
            'total_creados': query.count(),
            'total_payment': query_payment.count()

        }
        """
        planes = []
        for table_obj in table_headers:
            plan_query = query.filter(plan__arc_pricecode=table_obj.get('arc_pricecode'))
            planes.append(plan_query.count())

        row['planes_totales'] = planes
        """
        detalle_transtaction = []
        for table_obj in table_headers:
            product_query = query.filter(plan__product__arc_sku=table_obj.get('arc_sku'))
            #producto.append(product_query.count())
            
            payments_query = query_payment.filter(subscription__plan__product__arc_sku=table_obj.get('arc_sku'))
            #payments.append(payments_query.count())

            detalle_transtaction.append(
                {
                    'altas_totales': product_query.count(),
                    'payments_totales': payments_query.count()
                }
            )

        row['detalle_transtaction'] = detalle_transtaction


        return row


class RenovationReportView(View):
    def get(self, request, *args, **kwargs):
        template = loader.get_template('admin/report/renovation_report.html')
        context = {
            'form': RangeDateForm,
            'sites': ''
        }
        return HttpResponse(template.render(context, request))


class SubscriptionRepeatedReport(View):
    """
        Cantidad de suscripciones repetidas
    """

    def get(self, request, *args, **kwargs):
        template = loader.get_template('admin/paywall/subscription_repeated.html')

        query_string = """
            SELECT  1 as id, arcsubs_arcuser.uuid, COUNT(arcsubs_arcuser.uuid) as dcount
            FROM paywall_subscription
            INNER JOIN arcsubs_arcuser ON paywall_subscription.arc_user_id = arcsubs_arcuser.id
            GROUP BY (arcsubs_arcuser.uuid)
            HAVING (COUNT(arcsubs_arcuser.uuid))>1"""
        users = Subscription.objects.raw(query_string)

        context = {
            'users': users
        }
        return HttpResponse(template.render(context, request))

    def post(self, request, *args, **kwargs):
        template = loader.get_template('admin/paywall/subscription_repeated.html')
        site = request.POST.get('site', '')
        state = request.POST.getlist('state[]', '')
        state = tuple(state)
        if len(state) == 1:
            state = str(state).replace(",", "")

        if site and state:
            query_string = """
                SELECT  1 as id, arcsubs_arcuser.uuid, COUNT(arcsubs_arcuser.uuid) as dcount
                FROM paywall_subscription
                INNER JOIN arcsubs_arcuser ON paywall_subscription.arc_user_id = arcsubs_arcuser.id
                INNER JOIN paywall_partner ON paywall_subscription.partner_id = paywall_partner.id
                WHERE paywall_subscription.state in {state} and paywall_partner.partner_code = \'{site}\'
                GROUP BY (arcsubs_arcuser.uuid)
                HAVING (COUNT(arcsubs_arcuser.uuid))>1""".format(state=state, site=site)

        elif site and not state:
            query_string = """
                SELECT  1 as id, arcsubs_arcuser.uuid, COUNT(arcsubs_arcuser.uuid) as dcount
                FROM paywall_subscription
                INNER JOIN arcsubs_arcuser ON paywall_subscription.arc_user_id = arcsubs_arcuser.id
                INNER JOIN paywall_partner ON paywall_subscription.partner_id = paywall_partner.id
                WHERE paywall_partner.partner_code = \'{site}\'
                GROUP BY (arcsubs_arcuser.uuid)
                HAVING (COUNT(arcsubs_arcuser.uuid))>1""".format(site=site)

        elif state and not site:
            query_string = """
                SELECT  1 as id, arcsubs_arcuser.uuid, COUNT(arcsubs_arcuser.uuid) as dcount
                FROM paywall_subscription
                INNER JOIN arcsubs_arcuser ON paywall_subscription.arc_user_id = arcsubs_arcuser.id
                WHERE paywall_subscription.state in {state}
                GROUP BY (arcsubs_arcuser.uuid)
                HAVING (COUNT(arcsubs_arcuser.uuid))>1""".format(state=state)

        else:
            query_string = """
                SELECT  1 as id, arcsubs_arcuser.uuid, COUNT(arcsubs_arcuser.uuid) as dcount
                FROM paywall_subscription
                INNER JOIN arcsubs_arcuser ON paywall_subscription.arc_user_id = arcsubs_arcuser.id
                GROUP BY (arcsubs_arcuser.uuid)
                HAVING (COUNT(arcsubs_arcuser.uuid))>1"""

        users = Subscription.objects.raw(query_string)

        # Subscription.objects.filter(payment_profile__arc_user__uuid=)
        context = {
            'users': users,
            'estado': list(state),
            'total': len(list(users)),
            'site': site
        }
        print(site)
        print(state)
        return HttpResponse(template.render(context, request))


class LongPeridTimeSubscriptions(View):
    """
            Cantidad de suscripciones repetidas
        """

    def days_between(self, d1, d2):
        try:
            return abs((d2 - d1).days)
        except Exception:
            return 0

    def get(self, request, *args, **kwargs):
        template = loader.get_template('admin/paywall/long_period_time.html')
        list_subscription = []

        context = {
            'form': RangeDateForm,
            'list_subscription': list_subscription
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

    def post(self, request, *args, **kwargs):
        template = loader.get_template('admin/paywall/long_period_time.html')
        site = request.POST.get('site', '')
        """
        form = RangeDateForm(request.POST or None)

        if request.POST.get('days_quantity', ''):
            days_ = request.POST.get('days_quantity', '')

            if form.is_valid():
                start_date = self.start_day(form.cleaned_data.get('start_date'))
                end_date = self.end_day(form.cleaned_data.get('end_date'))

            list_subscription = []
            all_subscriptions = Subscription.objects.filter(
                data__currentPaymentMethod__paymentPartner='PayULATAM'
            )
            for obj_subs in all_subscriptions:
                if site and start_date and end_date:
                    payments = Payment.objects.filter(
                        subscription=obj_subs,
                        subscription__partner__partner_code=site,
                        date_payment__range=self.range_to_timestamp(start_date, end_date)
                    ).order_by('date_payment')

                    last_date_payment = ''
                    list_payment_register = []
                    flag_append = False
                    list_days = []
                    for payment_obj in payments:
                        if last_date_payment:
                            list_payment_register.append(payment_obj.date_payment)
                            validate_long_days = self.days_between(last_date_payment, payment_obj.date_payment) > int(days_)

                            if validate_long_days:
                                flag_append = True
                                list_days.append({
                                    'dias': self.days_between(last_date_payment, payment_obj.date_payment),
                                    'day_start': self.format_date(last_date_payment),
                                    'day_end': self.format_date(payment_obj.date_payment)
                                })

                        last_date_payment = payment_obj.date_payment
                    if flag_append:
                        list_subscription.append({
                            'subscription': self.get_data(obj_subs),
                            'user_login': self.get_user(obj_subs),
                            'payment': self.get_invoice(obj_subs),
                            'dias': list_days,
                            'payments': self.get_payments(obj_subs)
                        })

            context = {
                'form': form,
                'list_subscription': list_subscription,
                'days_gestion': 'days_gestion',
                'days_comercio': 'days_comercio',
                'days_quantity': days_
            }
        else:
            context = {
                'form': form,
                'message': 'Ingrese el numero de días'
            }
        """
        report = ReportLongPeriodTime.objects.get(
            site=site
        )
        context = report.data
        context['site'] = site
        return HttpResponse(template.render(context, request))

    def format_date(self, obj):
        try:
            tz = timezone.get_current_timezone()
            tz_date = obj.astimezone(tz)
            return formats.date_format(tz_date, "b. d, Y").capitalize()
        except Exception as e:
            return str(e)

    def get_user(self, obj):
        return obj.arc_user.get_display_html() if obj.arc_user_id else '-'

    def get_data(self, obj):
        tz = timezone.get_current_timezone()
        tz_created = obj.starts_date.astimezone(tz)
        title = obj.plan.plan_name if obj.plan_id else ''
        title += ' [{}]'.format(obj.campaign.get_category()) if obj.campaign_id else ' [--]'

        if obj.state == Subscription.ARC_STATE_ACTIVE:
            name_icon = 'full'
        elif obj.state == Subscription.ARC_STATE_CANCELED or obj.state == Subscription.ARC_STATE_SUSPENDED:
            name_icon = 'half'
        elif obj.state == Subscription.ARC_STATE_TERMINATED:
            name_icon = 'empty'
        else:
            name_icon = ''

        return format_html(
            '<strong>{title}</strong></br>'
            '<i class="fas fa-key"></i> ID {key}</br>'
            '<i class="fas fa-arrow-circle-up"></i> <strong>{created}</strong></br>'
            '<i class="fas fa-newspaper"></i> {site}</br>'
            '<i class="fas fa-battery-{name_icon}"></i> {state}',
            title=title,
            site=obj.partner,
            key=obj.arc_id,
            created=formats.date_format(tz_created, settings.DATETIME_FORMAT),
            state=obj.get_state_display(),
            name_icon=name_icon
        )

    def get_invoice(self, obj):
        payment_profile_link = '/admin/paywall/paymentprofile/{}/change/'.format(
            obj.payment_profile.id
        ) if obj.payment_profile else '#'
        brand_email = obj.payment_profile.portal_email if obj.payment_profile else '--'

        tz = timezone.get_current_timezone()

        try:
            tz_date = obj.starts_date.astimezone(tz)
            date_start_suscription = formats.date_format(tz_date, settings.DATETIME_FORMAT)
        except Exception as name_exception:
            date_start_suscription = 'Error en la fecha de suscripcion' + str(name_exception)

        return format_html(
            '<i class="fas fa-id-card fa-sm"></i> {payment_profile} '
            '<a href="{payment_profile_link}" target="_blank"><small>(ver)</small></a></br>'
            '<i class="fas fa-calendar-alt"></i> {date}</br>'
            '<i class="fas fa-at"></i> {email_pago}</br>',
            payment_profile=obj.payment_profile or '--',
            payment_profile_link=payment_profile_link,
            date=date_start_suscription,
            email_pago=brand_email
        )

    def get_payments(self, obj):
        if not obj.data or not obj.data.get('salesOrders'):
            return '----'

        html = ''

        for order in obj.data['salesOrders']:
            _date = timestamp_to_datetime(order['orderDateUTC'])

            html += '<span title="{date_detail}">{date} • S/ {amount}</span></br>'.format(
                amount=order['total'],
                date_detail=formats.localize(_date),
                date=formats.date_format(_date, settings.DATE_FORMAT),
            )

        return format_html(html)
