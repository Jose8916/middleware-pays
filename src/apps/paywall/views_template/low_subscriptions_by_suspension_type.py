from datetime import datetime, timedelta
from django.shortcuts import render
from django.db.models import Q, Count, DateTimeField
from django.http import HttpResponse
from django.template import loader
from django.views import View
from apps.paywall.models import Subscription, LowBySuspension, EventTypeSuspension
from django.db.models.functions import TruncDay, Trunc

import pytz
from dateutil.relativedelta import relativedelta, MO

TIMEZONE = pytz.timezone('America/Lima')


class LowSubscriptionsBySuspensionType(View):
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
        template = loader.get_template('admin/report/low_subscriptions_by_suspension_type.html')
        list_color = [
            'rgb(0, 0, 255)',  # BLUE  # 0000FF
            'rgb(192, 192, 192)',  # silver
            'rgb(128, 128, 128)',  # GRAY  # 808080
            'rgb(0, 0, 0)',  # BLACK  # 000000
            'rgb(255, 0, 0)',  # RED  # FF0000
            'rgb(128, 0, 0)',  # MAROON  # 800000
            'rgb(255, 255, 0)',  # YELLOW  # FFFF00
            'rgb(128, 128, 0)',  # OLIVE  # 808000
            'rgb(0, 255, 0)',  # LIME  # 00FF00
            'rgb(0, 128, 0)',  # GREEN  # 008000
            'rgb(0, 255, 255)',  # AQUA  # 00FFFF
            'rgb(0, 128, 128)',  # TEAL  # 008080
            'rgb(0, 0, 128)',  # NAVY  # 000080
            'rgb(255, 0, 255)',  # FUCHSIA  # FF00FF
            'rgb(128, 0, 128)'  # PURPLE  # 800080
        ]

        list_days = []
        event_types = EventTypeSuspension.objects.all()

        for event_type in event_types:
            dict_type_suspension = {}
            type_suspension_count = LowBySuspension.objects.filter(
                event_type=event_type.name
            ).count()
            dict_type_suspension[event_type.name] = type_suspension_count
            dict_type_suspension["name"] = event_type.name
            list_days.append(dict_type_suspension)

        # armando grafico
        count_color = 0
        list_name = []
        list_count = []

        for type_error in list_days:
            list_name.append(type_error.get('name', ''))
            list_count.append(type_error[type_error.get('name', '')])

        data_graph = {
            'labels': list_name,
            'datasets': [{
                    'label': 'Bajas totales por suspención',
                    'backgroundColor': list_color[count_color],
                    'borderColor': list_color[count_color],
                    'data': list_count
                }]
        }

        context = {
            'data_graph': data_graph,
            'type_report': 'bajas_por_tipo',
            'reportes': list_days
        }
        return HttpResponse(template.render(context, request))

    def data_graph_all(self, event_types, color, sites):
        list_days = []

        for event_type in event_types:
            dict_type_suspension = {}
            type_suspension_filter = LowBySuspension.objects.filter(
                event_type=event_type.name
            )

            if sites:
                type_suspension_filter = type_suspension_filter.filter(
                    subscription__partner__partner_code=sites
                )
            dict_type_suspension[event_type.name] = type_suspension_filter.count()
            dict_type_suspension["name"] = event_type.name
            list_days.append(dict_type_suspension)

        # armando grafico
        count_color = 0
        list_name = []
        list_count = []

        for type_error in list_days:
            list_name.append(type_error.get('name', ''))
            list_count.append(type_error[type_error.get('name', '')])

        return {
            'labels': list_name,
            'datasets': [{
                'label': 'Bajas totales por suspención',
                'backgroundColor': color,
                'borderColor': color,
                'data': list_count
            }]
        }

    def data_graph(self, date_to_graph, event_types, color, sites):
        list_days = []
        for event_type in event_types:
            dict_type_suspension = {}
            type_suspension_filter = LowBySuspension.objects.filter(
                subscription__date_anulled__month=date_to_graph.month,
                subscription__date_anulled__year=date_to_graph.year,
                event_type=event_type.name
            )

            if sites:
                type_suspension_filter = type_suspension_filter.filter(
                    subscription__partner__partner_code=sites
                )

            dict_type_suspension[event_type.name] = type_suspension_filter.count()
            dict_type_suspension["name"] = event_type.name
            list_days.append(dict_type_suspension)

        # armando grafico
        list_name = []
        list_count = []

        for type_error in list_days:
            list_name.append(type_error.get('name', ''))
            list_count.append(type_error[type_error.get('name', '')])

        return {
            'labels': list_name,
            'datasets': [{
                'label': date_to_graph.strftime("%B - %Y"),
                'backgroundColor': color,
                'borderColor': color,
                'data': list_count
            }]
        }

    def post(self, request, *args, **kwargs):
        template = loader.get_template('admin/report/low_subscriptions_by_suspension_type.html')
        list_color = [
            'rgb(0, 0, 255)',  # BLUE  # 0000FF
            'rgb(192, 192, 192)',  # silver
            'rgb(128, 128, 128)',  # GRAY  # 808080
            'rgb(0, 0, 0)',  # BLACK  # 000000
            'rgb(255, 0, 0)',  # RED  # FF0000
            'rgb(128, 0, 0)',  # MAROON  # 800000
            'rgb(255, 255, 0)',  # YELLOW  # FFFF00
            'rgb(128, 128, 0)',  # OLIVE  # 808000
            'rgb(0, 255, 0)',  # LIME  # 00FF00
            'rgb(0, 128, 0)',  # GREEN  # 008000
            'rgb(0, 255, 255)',  # AQUA  # 00FFFF
            'rgb(0, 128, 128)',  # TEAL  # 008080
            'rgb(0, 0, 128)',  # NAVY  # 000080
            'rgb(255, 0, 255)',  # FUCHSIA  # FF00FF
            'rgb(128, 0, 128)'  # PURPLE  # 800080
        ]
        start_date = request.POST.get('start_date', '')
        if start_date:
            start_date = datetime.strptime(start_date, '%m/%Y')
        end_date = request.POST.get('end_date', '')
        sites = request.POST.get('sites', '')
        data_graph = {}

        event_types = EventTypeSuspension.objects.all()
        list_data_graph = []
        if end_date and start_date:
            end = datetime.strptime(end_date, '%m/%Y')
            r = relativedelta(end, start_date)
            for count in range(r.months + 1):
                date_start = start_date + relativedelta(months=count)
                data_graph = self.data_graph(date_start, event_types, list_color[count], sites)
                list_data_graph.append(data_graph)
        if start_date and not end_date:
            list_data_graph.append(self.data_graph(start_date, event_types, list_color[0]), sites)

        width_div = 100
        if list_data_graph:
            if len(list_data_graph) >= 3:
                width_div = 33
            elif len(list_data_graph) == 2:
                width_div = 49

        data_graph_main = self.data_graph_all(event_types, list_color[2], sites)
        context = {
            'list_data_graph': list_data_graph,
            'data_graph': data_graph_main,
            'type_report': 'bajas_por_tipo',
            'width_div': width_div,
            'sites': sites
        }
        return HttpResponse(template.render(context, request))
