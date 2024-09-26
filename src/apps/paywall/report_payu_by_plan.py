from datetime import datetime, timedelta

from django.http import HttpResponse
from django.template import loader
from django.utils.timezone import get_default_timezone
from django.views import View

from .forms import RangeDateForm
from .models import Plan, Subscription, Payment


class SalesByPlanPayuReportView(View):
    def get(self, request, *args, **kwargs):
        template = loader.get_template('admin/report/sales_report_plans.html')
        context = {
            'form': RangeDateForm,
            'sites': ''
        }
        return HttpResponse(template.render(context, request))

    def table_headers(self):
        table_headers = []

        plans = Plan.objects.filter(state=True)

        for plan in plans:
            if plan.arc_pricecode:
                try:
                    plan.partner.partner_name

                except Exception:
                    continue

                else:
                    if plan.partner.partner_code == 'gestion':
                        color = 'FF7733'
                    else:
                        color = 'yellow'

                    table_headers.append(
                        {
                            'name_plan': plan.plan_name + ' - ' + plan.partner.partner_name,
                            'arc_pricecode': plan.arc_pricecode,
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
            total_bajas = self.get_bajas_base(start_date, end_date)
            range_date_search = end_date - start_date

            table_headers = self.table_headers()

            for count in range(range_date_search.days + 1):
                day = start_date + timedelta(days=count)
                queryset_base = self.get_queryset_base(day, day)
                query_payment = self.get_payment_base(day, day)
                query_bajas = self.get_bajas_base(day, day)

                queries = self.get_row_data(day, queryset_base, table_headers, query_payment, query_bajas)
                table_data.append(queries)
                table_footer = self.get_row_totales(total_subscriptions, total_payments, table_headers, total_bajas)

        sum_altas = 0
        sum_pagos = 0
        sum_bajas = 0
        for footer in table_footer:
            sum_altas = sum_altas + int(footer.get('altas_total', ''))
            sum_pagos = sum_pagos + int(footer.get('pagos_total', ''))
            sum_bajas = sum_bajas + int(footer.get('bajas_total', ''))

        context = {
            'form': form,
            'table_data': table_data,
            'table_headers': table_headers,
            'table_footer': table_footer,
            'total_altas': sum_altas,
            'total_cobros': sum_pagos,
            'total_bajas': sum_bajas,
            'bundle': ['7NK9SV', 'OKLLPH', 'NO07ET', 'UJWWFG', 'DD0DVZ', 'CSGJMY']
        }
        template = loader.get_template('admin/report/sales_report_plans.html')
        return HttpResponse(template.render(context, request))

    def get_queryset_base(self, start_date, end_date):
        queryset = Subscription.objects.filter(
            starts_date__range=self.range_to_timestamp(start_date, end_date),
            data__currentPaymentMethod__paymentPartner__contains="PayULATAM",
        )
        return queryset

    def get_payment_base(self, start_date, end_date):
        # queryset = Subscription.objects.filter(
        #     data__paymentHistory=
        #     created__range=self.range_to_timestamp(start_date, end_date)
        # )
        payment = Payment.objects.filter(
            created__range=self.range_to_timestamp(start_date, end_date)
        )
        return payment

    def get_bajas_base(self, start_date, end_date):
        queryset_bajas = Subscription.objects.filter(
            date_anulled__range=self.range_to_timestamp(start_date, end_date),
            data__currentPaymentMethod__paymentPartner__contains="PayULATAM",
        )
        return queryset_bajas

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

    def get_row_totales(self, query, query_payment, table_headers, query_bajas):

        producto = []
        for table_obj in table_headers:
            plan_query = query.filter(plan__arc_pricecode=table_obj.get('arc_pricecode'))
            payment_query = query_payment.filter(subscription__plan__arc_pricecode=table_obj.get('arc_pricecode'))
            bajas_query = query_bajas.filter(plan__arc_pricecode=table_obj.get('arc_pricecode'))

            producto.append(
                {
                    'altas_total': plan_query.count(),
                    'pagos_total': payment_query.count(),
                    'bajas_total': bajas_query.count(),
                    'arc_pricecode': table_obj.get('arc_pricecode')
                }
            )

        return producto

    def get_row_data(self, day, query, table_headers, query_payment, query_bajas):
        row = {
            'day': day,
            'total_creados': query.count(),
            'total_payment': query_payment.count(),
            'total_bajas': query_bajas.count()
        }

        detalle_transtaction = []
        for table_obj in table_headers:
            plan_query = query.filter(plan__arc_pricecode=table_obj.get('arc_pricecode'))
            payments_query = query_payment.filter(subscription__plan__arc_pricecode=table_obj.get('arc_pricecode'))
            bajas_query = query_bajas.filter(plan__arc_pricecode=table_obj.get('arc_pricecode'))

            detalle_transtaction.append(
                {
                    'altas_totales': plan_query.count(),
                    'payments_totales': payments_query.count(),
                    'bajas_count': bajas_query.count(),
                    'arc_pricecode': table_obj.get('arc_pricecode')
                }
            )

        row['detalle_transtaction'] = detalle_transtaction

        return row
