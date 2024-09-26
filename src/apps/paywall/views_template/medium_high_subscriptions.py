from datetime import datetime, timedelta

from django.http import HttpResponse
from django.template import loader
from django.utils.timezone import get_default_timezone
from django.views import View

from apps.paywall.models import Plan, Subscription, Payment, PaymentTracking


class HighSubscriptionsByMediumReportView(View):
    """
        Clase que maneja el reporte de altas por medio
    """

    def get(self, request, *args, **kwargs):
        template = loader.get_template('admin/report/medium_high_subscriptions.html')
        context = {
            'form': '',
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

    def load_data_set(self, table_data):
        # armando grafico
        list_color = [
            'rgb(0, 0, 255)',  # BLUE  # 0000FF
            'rgb(255, 0, 0)',  # RED  # FF0000
            'rgb(0, 0, 0)',  # BLACK  # 000000
            'rgb(255, 255, 0)',  # YELLOW  # FFFF00
            'rgb(128, 0, 128)'  # PURPLE  # 800080
        ]

        data_sets = [
            {
                'label': 'Fia',
                'backgroundColor': list_color[0],
                'borderColor': list_color[0],
                'data': [row['total_by_day_fia'] for row in table_data]
            },
            {
                'label': 'Landing',
                'backgroundColor': list_color[1],
                'borderColor': list_color[1],
                'data': [row['total_by_day_landing'] for row in table_data]
            },
            {
                'label': 'Organico',
                'backgroundColor': list_color[2],
                'borderColor': list_color[2],
                'data': [row['total_by_day_organico'] for row in table_data]
            },
            {
                'label': 'Paywall',
                'backgroundColor': list_color[3],
                'borderColor': list_color[3],
                'data': [row['total_by_day_paywall'] for row in table_data]
            },
            {
                'label': 'Premium',
                'backgroundColor': list_color[4],
                'borderColor': list_color[4],
                'data': [row['total_by_day_premium'] for row in table_data]
            }
        ]
        return data_sets

    def post(self, request, *args, **kwargs):
        template = loader.get_template('admin/report/medium_high_subscriptions.html')

        table_data = []
        start_day = request.POST.get('start_day', '')
        end_day = request.POST.get('end_day', '')
        start_date = self.start_day(datetime.strptime(start_day, '%d/%m/%Y'))
        end_date = self.end_day(datetime.strptime(end_day, '%d/%m/%Y'))
        total_fia = self.get_queryset_base(start_date, end_date, 'fia')
        total_landing = self.get_queryset_base(start_date, end_date, 'landing')
        total_organico = self.get_queryset_base(start_date, end_date, 'organico')
        total_paywall = self.get_queryset_base(start_date, end_date, 'paywall')
        total_premium = self.get_queryset_base(start_date, end_date, 'premium')

        range_date_search = end_date - start_date

        table_headers = self.table_headers()

        for count in range(range_date_search.days + 1):
            day = start_date + timedelta(days=count)

            table_data.append({
                'day': day.strftime("%d-%m-%Y"),
                'total_by_day_fia': self.get_queryset_base(day, day, 'fia'),
                'total_by_day_landing': self.get_queryset_base(day, day, 'landing'),
                'total_by_day_organico': self.get_queryset_base(day, day, 'organico'),
                'total_by_day_paywall': self.get_queryset_base(day, day, 'paywall'),
                'total_by_day_premium': self.get_queryset_base(day, day, 'premium')
            })

        data_sets = self.load_data_set(table_data)
        data_graph = {
            'labels': [sub['day'] for sub in table_data],
            'datasets': data_sets
        }

        context = {
            'table_data': table_data,
            'table_headers': table_headers,
            'table_footer': '',
            'total_fia': total_fia,
            'total_landing': total_landing,
            'total_organico': total_organico,
            'total_paywall': total_paywall,
            'total_premium': total_premium,
            'data_graph': data_graph
        }

        return HttpResponse(template.render(context, request))

    def get_queryset_base(self, start_date, end_date, medium):
        queryset = PaymentTracking.objects.filter(
            subscription__starts_date__range=self.range_to_timestamp(start_date, end_date),
            medium=medium
        ).count()
        return queryset

    def get_payment_base(self, start_date, end_date):
        payment = Payment.objects.filter(
            date_payment__range=self.range_to_timestamp(start_date, end_date),
            pa_origin='RECURRENCE'
        )
        return payment

    def get_bajas_base(self, start_date, end_date):
        queryset_bajas = Subscription.objects.filter(
            date_anulled__range=self.range_to_timestamp(start_date, end_date)
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
            'day': day.strftime("%d-%m-%Y"),
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
                    'renovaciones_totales': payments_query.count(),
                    'bajas_count': bajas_query.count(),
                    'arc_pricecode': table_obj.get('arc_pricecode')
                }
            )

        row['detalle_transtaction'] = detalle_transtaction

        return row
