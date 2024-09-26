from datetime import datetime, timedelta
from django.shortcuts import render
from django.db.models import Q, Count, DateTimeField
from django.http import HttpResponse
from django.template import loader
from django.views import View
from apps.paywall.models import Subscription, LowBySuspension, EventTypeSuspension
from django.db.models.functions import TruncDay, Trunc
from django.utils.timezone import get_default_timezone

import pytz
from dateutil.relativedelta import relativedelta, MO

TIMEZONE = pytz.timezone('America/Lima')


class LowSubscriptionsBySuspension(View):
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
        template = loader.get_template('admin/report/low_subscriptions_by_suspension.html')
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
            'rgb(128, 0, 128)',  # PURPLE  # 800080
            'rgb((0, 206, 209)',  # dark turquoise
            'rgb(221, 160, 221)'  # plum
        ]
        start_date = datetime.now(TIMEZONE) - relativedelta(months=17)
        end_date = datetime.now(TIMEZONE)

        list_days = []
        for count in range(3):
            dict_type_suspension = {}
            start_date = start_date + relativedelta(months=1)
            event_types = EventTypeSuspension.objects.all()
            for event_type in event_types:
                type_suspension_count = LowBySuspension.objects.filter(
                    subscription__date_anulled__month=start_date.month,
                    subscription__date_anulled__year=start_date.year,
                    event_type=event_type.name
                ).count()
                dict_type_suspension[event_type.name] = type_suspension_count

            dict_type_suspension["name"] = start_date.strftime("%B - %Y")
            list_days.append(dict_type_suspension)

        # armando grafico
        data_sets = []
        count_color = 0
        for event_type in event_types:
            data_sets.append(
                {
                    'label': event_type.name,
                    'backgroundColor': list_color[count_color],
                    'borderColor': list_color[count_color],
                    'data': [sub[event_type.name] for sub in list_days]
                }
            )
            count_color = count_color + 1

        data_graph = {
            'labels': [sub['name'] for sub in list_days],
            'datasets': data_sets
        }

        context = {
            'data_graph': data_graph,
            'type_report': 'bajas_por_tipo',
            'start_date': start_date.strftime("%d-%m-%Y"),
            'end_date': end_date.strftime("%d-%m-%Y"),
            'reportes': list_days
        }
        return HttpResponse(template.render(context, request))

    def filter_by_months(self, start_date, event_types, sites, list_color):
        list_days = []
        for count in range(3):
            dict_type_suspension = {}
            start_date = start_date + relativedelta(months=1)

            for event_type in event_types:
                type_suspension_filter = LowBySuspension.objects.filter(
                    subscription__date_anulled__month=start_date.month,
                    subscription__date_anulled__year=start_date.year,
                    event_type=event_type.name
                )
                if sites:
                    type_suspension_filter = type_suspension_filter.filter(
                        subscription__partner__partner_code=sites
                    )
                dict_type_suspension[event_type.name] = type_suspension_filter.count()

            dict_type_suspension["name"] = start_date.strftime("%B - %Y")
            list_days.append(dict_type_suspension)

        # armando grafico
        data_sets = []
        count_color = 0
        for event_type in event_types:
            data_sets.append(
                {
                    'label': event_type.name,
                    'backgroundColor': list_color[count_color],
                    'borderColor': list_color[count_color],
                    'data': [sub[event_type.name] for sub in list_days]
                }
            )
            count_color = count_color + 1

        data_graph = {
            'labels': [sub['name'] for sub in list_days],
            'datasets': data_sets
        }

        return {
            'data_graph': data_graph,
            'type_report': 'bajas_por_tipo ' + sites,
            'start_date': start_date.strftime("%d-%m-%Y"),
            'reportes': list_days,
            'sites': sites
        }

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

    def filter_by_days(self, start_date, end_date, event_types, sites, list_color):
        range_date_search = end_date - start_date
        list_days = []
        table_data = []

        for count in range(range_date_search.days + 1):
            day = start_date + timedelta(days=count)
            dict_type_suspension = {}
            list_event_type = []
            for event_type in event_types:
                queryset = LowBySuspension.objects.filter(
                    subscription__date_anulled__range=self.range_to_timestamp(day, day),
                    event_type=event_type.name
                )
                if sites:
                    queryset = queryset.filter(
                        subscription__partner__partner_code=sites
                    )
                dict_type_suspension[event_type.name] = queryset.count()
                list_event_type.append({
                    'name_type': event_type.name,
                    'cantidad': queryset.count()
                })

            table_data.append({
                'day': day.strftime("%d-%m-%Y"),
                'list_event_type': list_event_type
            })
            dict_type_suspension["name"] = day.strftime("%d-%m-%Y")
            list_days.append(dict_type_suspension)

        # armando grafico
        data_sets = []
        count_color = 0
        for event_type in event_types:
            data_sets.append(
                {
                    'label': event_type.name,
                    'backgroundColor': list_color[count_color],
                    'borderColor': list_color[count_color],
                    'data': [sub[event_type.name] for sub in list_days]
                }
            )
            count_color = count_color + 1

        data_graph = {
            'labels': [sub['day'] for sub in table_data],
            'datasets': data_sets
        }

        return {
            'data_graph': data_graph,
            'type_report': 'bajas_por_tipo ' + sites,
            'start_date': start_date.strftime("%d-%m-%Y"),
            'reportes': list_days,
            'sites': sites,
            'event_types': event_types,
            'table_data': table_data
        }

    def post(self, request, *args, **kwargs):
        template = loader.get_template('admin/report/low_subscriptions_by_suspension.html')
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
            'rgb(128, 0, 128)',  # PURPLE  # 800080
            'rgb(0, 0, 255)',  # BLUE  # 0000FF
            'rgb(192, 192, 192)',  # silver
            'rgb(128, 128, 128)',  # GRAY  # 808080
            'rgb(0, 0, 0)',  # BLACK  # 000000
            'rgb(255, 0, 0)',  # RED  # FF0000
            'rgb(128, 0, 0)',  # MAROON  # 800000
            'rgb(255, 255, 0)',  # YELLOW  # FFFF00
            'rgb(128, 128, 0)'  # OLIVE  # 808000
        ]
        start_date = datetime.now(TIMEZONE) - relativedelta(months=17)
        end_date = datetime.now(TIMEZONE)
        sites = request.POST.get('sites', '')
        periodo = request.POST.get('periodo', '')

        event_types = EventTypeSuspension.objects.all()

        if periodo == 'meses':
            context = self.filter_by_months(start_date, event_types, sites, list_color)

        if periodo == 'dias' and request.POST.get('start_day', '') and request.POST.get('end_day', ''):
            start_day = request.POST.get('start_day', '')
            end_day = request.POST.get('end_day', '')
            start_day = self.start_day(datetime.strptime(start_day, '%d/%m/%Y'))
            end_day = self.end_day(datetime.strptime(end_day, '%d/%m/%Y'))
            context = self.filter_by_days(start_day, end_day, event_types, sites, list_color)

        return HttpResponse(template.render(context, request))
