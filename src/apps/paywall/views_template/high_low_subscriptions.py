from datetime import datetime, timedelta
from django.shortcuts import render
from django.db.models import Q, Count, DateTimeField
from django.http import HttpResponse
from django.template import loader
from django.views import View
from apps.paywall.models import Subscription, Plan
from django.db.models.functions import TruncDay, Trunc

import pytz
from dateutil.relativedelta import relativedelta, MO

TIMEZONE = pytz.timezone('America/Lima')


class HightLowSubscriptions(View):
    """

    """
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
            starts.astimezone(TIMEZONE),
            ends.astimezone(TIMEZONE)
        )

    def min_date(self, date_input):
        min_date = datetime.combine(
            date_input,
            datetime.min.time()
        )
        return min_date.astimezone(TIMEZONE),

    def get(self, request, *args, **kwargs):
        template = loader.get_template('admin/report/high_low_subscriptions.html')
        list_color = [
            'rgb(0, 0, 255)',  # BLUE  # 0000FF
            'rgb(192, 192, 192)',  # silver
            'rgb(0, 0, 0)',  # BLACK  # 000000
            'rgb(255, 0, 0)'  # RED  # FF0000
        ]
        start_date = datetime.now(TIMEZONE) - relativedelta(months=17)
        end_date = datetime.now(TIMEZONE)
        range_date_search = end_date - start_date
        planes = Plan.objects.all()
        list_dict_planes = []
        for plan in planes:
            try:
                list_dict_planes.append(
                    {
                        'id': plan.id,
                        'name': plan.plan_name + ' - ' + plan.partner.partner_name
                    }
                )
            except Exception:
                continue

        list_days = []

        for count in range(17):
            start_date = start_date + relativedelta(months=1)

            subscriptions_high_count = Subscription.objects.filter(
                starts_date__month=start_date.month,
                starts_date__year=start_date.year,
            ).count()

            subscriptions_low_count = Subscription.objects.filter(
                date_anulled__month=start_date.month,
                date_anulled__year=start_date.year,
            ).count()

            list_days.append({
                'name': start_date.strftime("%B - %Y"),
                'altas': subscriptions_high_count,
                'bajas': subscriptions_low_count
            })

        # armando grafico
        data_graph = {
            'labels': [sub['name'] for sub in list_days],
            'datasets': [{
                'label': 'Altas de Suscripciones',
                'backgroundColor': list_color[0],
                'borderColor': list_color[0],
                'data': [sub['altas'] for sub in list_days]
            },
            {
                'label': 'Bajas de Suscripciones',
                'backgroundColor': list_color[1],
                'borderColor': list_color[1],
                'data': [sub['bajas'] for sub in list_days]
            }]
        }

        context = {
            'data_graph': data_graph,
            'type_report': 'altas_bajas',
            'start_date': start_date.strftime("%d-%m-%Y"),
            'end_date': end_date.strftime("%d-%m-%Y"),
            'reportes': list_days,
            'planes': list_dict_planes
        }
        return HttpResponse(template.render(context, request))

    def post(self, request, *args, **kwargs):
        template = loader.get_template('admin/report/high_low_subscriptions.html')
        list_color = [
            'rgb(0, 0, 255)',  # BLUE  # 0000FF
            'rgb(192, 192, 192)',  # silver
            'rgb(0, 0, 0)',  # BLACK  # 000000
            'rgb(255, 0, 0)'  # RED  # FF0000
        ]
        start_date = datetime.now(TIMEZONE) - relativedelta(months=17)
        end_date = datetime.now(TIMEZONE)
        range_date_search = end_date - start_date
        planes_checkbox = request.POST.getlist('planes')
        sites = request.POST.get('sites', '')
        if sites:
            planes = Plan.objects.filter(partner__partner_code=sites)
        else:
            planes = Plan.objects.all()
        list_dict_planes = []
        for plan in planes:
            try:
                list_dict_planes.append(
                    {
                        'id': plan.id,
                        'name': plan.plan_name + ' - ' + plan.partner.partner_name
                    }
                )
            except Exception:
                continue

        list_days = []

        for count in range(17):
            start_date = start_date + relativedelta(months=1)

            subscriptions_high = Subscription.objects.filter(
                starts_date__month=start_date.month,
                starts_date__year=start_date.year,
            )
            if planes_checkbox:
                subscriptions_high = subscriptions_high.exclude(
                    plan__id__in=planes_checkbox
                )
            if sites:
                subscriptions_high = subscriptions_high.filter(
                    partner__partner_code=sites
                )

            subscriptions_low = Subscription.objects.filter(
                date_anulled__month=start_date.month,
                date_anulled__year=start_date.year,
            )
            if planes_checkbox:
                subscriptions_low = subscriptions_low.exclude(
                    plan__id__in=planes_checkbox
                )
            if sites:
                subscriptions_low = subscriptions_low.filter(
                    partner__partner_code=sites
                )
            list_days.append({
                'name': start_date.strftime("%B - %Y"),
                'altas': subscriptions_high.count(),
                'bajas': subscriptions_low.count()
            })

        # armando grafico
        data_graph = {
            'labels': [sub['name'] for sub in list_days],
            'datasets': [
                {
                    'label': 'Altas de Suscripciones ' + sites,
                    'backgroundColor': list_color[0],
                    'borderColor': list_color[0],
                    'data': [sub['altas'] for sub in list_days]
                },
                {
                    'label': 'Bajas de Suscripciones ' + sites,
                    'backgroundColor': list_color[1],
                    'borderColor': list_color[1],
                    'data': [sub['bajas'] for sub in list_days]
                }]
        }
        list_seleccionados = []

        for checkeado in planes_checkbox:
            list_seleccionados.append(int(checkeado))

        context = {
            'data_graph': data_graph,
            'type_report': 'altas_bajas',
            'start_date': start_date.strftime("%d-%m-%Y"),
            'end_date': end_date.strftime("%d-%m-%Y"),
            'reportes': list_days,
            'planes': list_dict_planes,
            'planes_checked': list_seleccionados,
            'sites': sites
        }
        return HttpResponse(template.render(context, request))
